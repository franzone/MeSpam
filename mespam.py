from ast import Import
import sys
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

class MeSpamFilter:

    def __init__(self):
        with open('mailboxes.yml', 'r') as stream:
            self.config = load(stream, Loader=Loader)['mailboxes']

    def run(self, mailbox='ALL'):
        if 'ALL' == mailbox or mailbox in self.config.keys():
            print('Running MeSpamFilter against {0} mailbox(s)'.format(mailbox))
            for mbox in self.config:
                if 'ALL' == mailbox or mbox == mailbox:
                    print(mbox, '->', self.config[mbox])
        else:
            print('Mailbox {0} Not Found'.format(mailbox))

    def process_mailbox(self, mailbox):
        print('Processing mailbox for {0}'.format(mailbox['email']))

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
