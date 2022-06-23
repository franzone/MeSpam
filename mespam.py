from ast import Import
from email.message import EmailMessage
import sys
import imaplib
import email, email.message, email.policy
import re
import traceback
import pprint
from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

class MeSpamFilter:

    def __init__(self):
        with open('mailboxes.yml', 'r') as stream:
            self.config = load(stream, Loader=Loader)['mailboxes']

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
                self.open_inbox(mailbox)
                mbox.select()
                typ, data = mbox.search(None, 'ALL')
                totalCount = len(data[0].split())
                print('Found {0} emails to process'.format(totalCount))
                for num in data[0].split():
                    try:
                        # Get the message
                        typ, data = mbox.fetch(num, '(BODY.PEEK[])')
                        msg = email.message_from_bytes(data[0][1], policy=email.policy.default)

                        # Get JUST the email address and domain
                        match = re.search(r'([\w\.-]+)(@[\w\.-]+)', msg['From'])
                        emailAddr = match.group(0)
                        emailDomain = match.group(2)

                        if emailAddr == mailbox['email']:
                            body = msg.get_body(('html', 'plain'))
                            if body:
                                if 'https://storage.googleapis.com' in body.get_content():

                                    print('THIS IS JUNK! SPAM IT! - {0}'.format(self.strip_non_ascii(msg['Subject'])))

                                    msgDateTuple = email.utils.parsedate_tz(msg['Date'])
                                    msgDateTm = email.utils.mktime_tz(msgDateTuple)

                                    # Copy the message to the SPAM folder
                                    mbox.append(mailbox['spam-folder'], '', imaplib.Time2Internaldate(msgDateTm), str(msg).encode('utf-8'))

                                    # Remove the message from the INBOX
                                    mbox.store(num, '+FLAGS', '\\Deleted')
                                    counter = counter + 1

                    except:
                        print('Error processing email', sys.exc_info()[0])
                        print(traceback.format_exc())
                
                # Expunge the INBOX
                mbox.expunge()

                print('Moved {0} of {1} emails to the SPAM folder'.format(counter, totalCount))

            except:
                print('Error processing inbox for {0}: {1}'.format(mailbox['email'], sys.exc_info()[0]))
                print(traceback.format_exc())
            finally:
                self.close_inbox(mbox)

    def open_inbox(self, mailbox):
        mbox = imaplib.IMAP4(mailbox['imap-host'])
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

    def strip_non_ascii(str):
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
