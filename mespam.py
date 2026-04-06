∏import sys
import os
import imaplib
import email, email.message, email.policy
import re
import traceback
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class MeSpamFilter:

    def __init__(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mailboxes.yml')
        with open(config_path, 'r') as stream:
            config = load(stream, Loader=Loader)
            self.config = config['mailboxes']
            self.global_patterns = config.get('patterns', [])

    def run(self, mailbox='ALL'):
        if 'ALL' == mailbox or mailbox in self.config.keys():
            print('Running MeSpamFilter against {0} mailbox(s)'.format(mailbox))
            for key in self.config:
                if 'ALL' == mailbox or key == mailbox:
                    self.process_mailbox(self.config[key])
        else:
            print('Mailbox {0} Not Found'.format(mailbox))

    def process_mailbox(self, mailbox):
        print('Processing mailbox for {0}'.format(mailbox['email']))
        mbox = self.open_inbox(mailbox)
        counter = 0
        if mbox:
            try:
                mbox.select()
                typ, data = mbox.search(None, 'FROM', mailbox['email'])
                nums = data[0].split()
                totalCount = len(nums)
                print('Found {0} emails to process'.format(totalCount))

                spam_nums = []
                for num in nums:
                    try:
                        # Fetch the full message for pattern matching
                        _, data = mbox.fetch(num, '(BODY.PEEK[])')
                        msg = email.message_from_bytes(data[0][1], policy=email.policy.default)

                        patterns = mailbox.get('patterns', self.global_patterns)
                        if self.matches_any_pattern(msg, mailbox['email'], patterns):

                            print('THIS IS JUNK! SPAM IT! - {0}'.format(self.strip_non_ascii(msg['Subject'])))

                            msgDateTuple = email.utils.parsedate_tz(msg['Date'])
                            msgDateTm = email.utils.mktime_tz(msgDateTuple)

                            # Copy the message to the SPAM folder
                            mbox.append(mailbox['spam-folder'], '', imaplib.Time2Internaldate(msgDateTm), str(msg).encode('utf-8'))

                            spam_nums.append(num)
                            counter = counter + 1

                    except Exception:
                        print('Error processing email', sys.exc_info()[0])
                        print(traceback.format_exc())

                # Batch-delete all spam messages at once
                if spam_nums:
                    mbox.store(b','.join(spam_nums), '+FLAGS', '\\Deleted')

                # Expunge the INBOX
                mbox.expunge()

                print('Moved {0} of {1} emails to the SPAM folder'.format(counter, totalCount))

            except Exception:
                print('Error processing inbox for {0}: {1}'.format(mailbox['email'], sys.exc_info()[0]))
                print(traceback.format_exc())
            finally:
                self.close_inbox(mbox)

    def open_inbox(self, mailbox):
        mbox = imaplib.IMAP4_SSL(mailbox['imap-host'])
        try:
            mbox.login(mailbox['email'], mailbox['password'])
            return mbox
        except imaplib.IMAP4.error as e:
            print('Error opening mbox: ', e)
        return None

    def close_inbox(self, mbox):
        print('Closing mbox')
        try:
            mbox.close()
            mbox.logout()
        except imaplib.IMAP4.error as e:
            print('Error closing inbox: ', e)
        return None

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
                    match = re.search(r'([\w\.-]+)(@[\w\.-]+)', msg['From'])
                    if not match or match.group(0) != mailbox_email:
                        return False

            elif condition == 'body-contains':
                if body_content is None:
                    body = msg.get_body(('html', 'plain'))
                    body_content = body.get_content() if body else ''
                if value not in body_content:
                    return False

            elif condition == 'body-matches':
                if body_content is None:
                    body = msg.get_body(('html', 'plain'))
                    body_content = body.get_content() if body else ''
                if not re.search(value, body_content):
                    return False

            elif condition == 'subject-contains':
                if subject is None:
                    subject = msg['Subject'] or ''
                if value not in subject:
                    return False

            elif condition == 'subject-matches':
                if subject is None:
                    subject = msg['Subject'] or ''
                if not re.search(value, subject):
                    return False

        return True

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
    o.run(mailbox)

    return 0

if __name__ == '__main__':
    sys.exit(main())
