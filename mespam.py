import sys
import os
import codecs
import imaplib
import email, email.policy, email.utils
import re
import traceback
import yaml

IMAP_TIMEOUT_SECONDS = 60


class MeSpamFilter:

    def __init__(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mailboxes.yml')
        with open(config_path, 'r') as stream:
            config = yaml.safe_load(stream)
            self.config = config['mailboxes']
            self.global_patterns = config.get('patterns') or []

    def run(self, mailbox='ALL'):
        '''Returns True if every requested mailbox was processed without error'''
        if 'ALL' != mailbox and mailbox not in self.config:
            print('Mailbox {0} Not Found'.format(mailbox))
            return False

        print('Running MeSpamFilter against {0} mailbox(s)'.format(mailbox))
        ok = True
        for key in self.config:
            if 'ALL' == mailbox or key == mailbox:
                try:
                    if not self.process_mailbox(self.config[key]):
                        ok = False
                except Exception:
                    # One broken mailbox (bad host, timeout, ...) must not stop the others
                    ok = False
                    print('Error processing mailbox {0}'.format(key))
                    print(traceback.format_exc())
        return ok

    def process_mailbox(self, mailbox):
        print('Processing mailbox for {0}'.format(mailbox['email']))
        patterns = mailbox.get('patterns', self.global_patterns) or []
        mbox = self.open_inbox(mailbox)
        if not mbox:
            return False

        ok = True
        try:
            self.check(mbox.select('INBOX'), 'SELECT INBOX')

            # Let the server narrow down the candidates so only likely spam is downloaded
            uids = set()
            for pattern in patterns:
                typ, data = mbox.uid('SEARCH', *self.search_criteria(pattern, mailbox['email']))
                self.check((typ, data), 'SEARCH')
                uids.update(data[0].split())
            uids = sorted(uids, key=int)
            print('Found {0} candidate emails to check'.format(len(uids)))

            spam_uids = []
            for uid in uids:
                try:
                    typ, data = mbox.uid('FETCH', uid, '(BODY.PEEK[])')
                    if typ != 'OK' or not data or not isinstance(data[0], tuple):
                        continue  # message disappeared since the search
                    msg = email.message_from_bytes(data[0][1], policy=email.policy.default)

                    if self.matches_any_pattern(msg, mailbox['email'], patterns):
                        print('THIS IS JUNK! SPAM IT! - {0}'.format(self.strip_non_ascii(self.header(msg, 'Subject'))))
                        spam_uids.append(uid)

                except Exception:
                    ok = False
                    print('Error processing email UID {0}'.format(uid.decode()))
                    print(traceback.format_exc())

            if spam_uids:
                self.move_messages(mbox, spam_uids, mailbox['spam-folder'])

            print('Moved {0} of {1} emails to the SPAM folder'.format(len(spam_uids), len(uids)))

        except Exception:
            ok = False
            print('Error processing inbox for {0}'.format(mailbox['email']))
            print(traceback.format_exc())
        finally:
            self.close_inbox(mbox)
        return ok

    def open_inbox(self, mailbox):
        mbox = imaplib.IMAP4_SSL(mailbox['imap-host'], timeout=IMAP_TIMEOUT_SECONDS)
        try:
            mbox.login(mailbox['email'], str(mailbox['password']))
            return mbox
        except imaplib.IMAP4.error as e:
            print('Error opening mbox: ', e)
            try:
                mbox.logout()
            except Exception:
                pass
        return None

    def close_inbox(self, mbox):
        print('Closing mbox')
        try:
            if mbox.state == 'SELECTED':
                # UNSELECT-style close: never expunge messages we did not handle ourselves
                mbox.unselect() if 'UNSELECT' in self.capabilities(mbox) else mbox.close()
            mbox.logout()
        except Exception as e:
            print('Error closing inbox: ', e)
        return None

    def capabilities(self, mbox):
        '''Capabilities as advertised after login (imaplib only caches the pre-login list)'''
        caps = getattr(mbox, '_mespam_caps', None)
        if caps is None:
            typ, data = mbox.capability()
            caps = set(data[0].decode('ascii', 'replace').upper().split()) if typ == 'OK' else set()
            mbox._mespam_caps = caps
        return caps

    def move_messages(self, mbox, uids, folder):
        '''Moves the messages server-side, byte-for-byte, without touching any other message'''
        uid_set = b','.join(uids).decode()
        folder = self.quote(folder)
        caps = self.capabilities(mbox)

        if 'MOVE' in caps:
            self.check(mbox.uid('MOVE', uid_set, folder), 'MOVE')
            return

        self.check(mbox.uid('COPY', uid_set, folder), 'COPY')
        self.check(mbox.uid('STORE', uid_set, '+FLAGS.SILENT', '(\\Deleted)'), 'STORE')
        if 'UIDPLUS' in caps:
            self.check(mbox.uid('EXPUNGE', uid_set), 'EXPUNGE')
        else:
            self.check(mbox.expunge(), 'EXPUNGE')

    def check(self, response, what):
        typ, data = response
        if typ != 'OK':
            raise imaplib.IMAP4.error('{0} failed: {1} {2}'.format(what, typ, data))

    def quote(self, value):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def search_criteria(self, pattern, mailbox_email):
        '''Builds an IMAP SEARCH that returns a superset of the messages matching the pattern.

        Only conditions the server can evaluate are included; every candidate is
        still verified locally by matches_pattern.
        '''
        keys = {'body-contains': 'BODY', 'subject-contains': 'SUBJECT'}
        criteria = []
        for condition, value in pattern.items():
            if condition == 'from-is-self' and value:
                criteria += ['FROM', self.quote(mailbox_email)]
            elif condition == 'sender-auth-fails' and value:
                criteria += ['HEADER', 'Authentication-Results', '"fail"']
            elif condition in keys and isinstance(value, str) and value.isascii() \
                    and value.strip() and '\r' not in value and '\n' not in value:
                criteria += [keys[condition], self.quote(value)]
        return criteria or ['ALL']

    def matches_any_pattern(self, msg, mailbox_email, patterns):
        '''Returns True if the email matches any of the configured spam patterns'''
        for pattern in patterns:
            if self.matches_pattern(msg, mailbox_email, pattern):
                return True
        return False

    def matches_pattern(self, msg, mailbox_email, pattern):
        '''Returns True if the email matches ALL conditions in a single pattern'''
        body_content = None
        subject = None

        for condition, value in pattern.items():
            if condition == 'from-is-self':
                if value:
                    sender = email.utils.parseaddr(self.header(msg, 'From'))[1]
                    if sender.lower() != mailbox_email.lower():
                        return False

            elif condition == 'sender-auth-fails':
                if value and not self.sender_auth_fails(msg):
                    return False

            elif condition in ('body-contains', 'body-matches'):
                if body_content is None:
                    body_content = self.body_text(msg)
                if condition == 'body-contains':
                    if value not in body_content:
                        return False
                elif not re.search(value, body_content):
                    return False

            elif condition in ('subject-contains', 'subject-matches'):
                if subject is None:
                    subject = self.header(msg, 'Subject')
                if condition == 'subject-contains':
                    if value not in subject:
                        return False
                elif not re.search(value, subject):
                    return False

            else:
                # An unknown condition must never widen what gets moved
                print('Ignoring pattern with unknown condition: {0}'.format(condition))
                return False

        return True

    def sender_auth_fails(self, msg):
        '''Returns True if the receiving server recorded that the sender was forged.

        Only the topmost Authentication-Results header is trusted: it is the one
        added by our own inbound server, anything below it may be attacker-supplied.
        A message with no such header (e.g. one saved straight into the mailbox)
        is never treated as a failure.
        '''
        for key, val in msg.raw_items():
            if key.lower() == 'authentication-results':
                results = dict(re.findall(r'\b(spf|dkim|dmarc)\s*=\s*(\w+)', str(val).lower()))
                if results.get('dkim') == 'pass' or results.get('dmarc') == 'pass':
                    return False
                return results.get('spf') in ('fail', 'softfail') or results.get('dmarc') == 'fail'
        return False

    def header(self, msg, name):
        '''Returns a header as text, tolerating missing or malformed headers'''
        try:
            return str(msg[name] or '')
        except Exception:
            for key, val in msg.raw_items():
                if key.lower() == name.lower():
                    return str(val)
            return ''

    def body_text(self, msg):
        '''Returns all text parts (plain and html) of the message as one string.

        Spam routinely declares bogus or unusual charsets (cp-850, windows-874, ...),
        so decoding never raises: unknown charsets fall back to a lossy decode,
        which still preserves the ASCII text the patterns look for.
        '''
        chunks = []
        for part in msg.walk():
            if part.get_content_maintype() != 'text' or part.get_content_disposition() == 'attachment':
                continue
            try:
                payload = part.get_payload(decode=True)
            except Exception:
                payload = None
            if isinstance(payload, bytes):
                chunks.append(self.decode(payload, part.get_content_charset()))
        return '\n'.join(chunks)

    def decode(self, payload, charset):
        candidates = []
        if charset:
            candidates.append(charset)
            # cp-850 -> cp850, windows-874 -> cp874
            candidates.append(re.sub(r'^(?:cp|windows|ibm)[-_ ]?(\d+)$', r'cp\1', charset.strip().lower()))
        for candidate in candidates:
            try:
                codecs.lookup(candidate)
            except (LookupError, ValueError):
                continue
            return payload.decode(candidate, errors='replace')
        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return payload.decode('latin-1')

    def strip_non_ascii(self, str):
        ''' Returns the string without non ASCII characters '''
        stripped = (c for c in str if 0 < ord(c) < 127)
        return ''.join(stripped)

def main() -> int:
    if len(sys.argv) >= 2:
        mailbox = sys.argv[1]
    else:
        mailbox = 'ALL'

    o = MeSpamFilter()
    return 0 if o.run(mailbox) else 1

if __name__ == '__main__':
    sys.exit(main())
