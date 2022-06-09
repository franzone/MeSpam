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
        print('Running MeSpamFilter against {0} mailbox(s)'.format(mailbox))
        for mbox in self.config:
            print(mbox, '->', self.config[mbox])

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
