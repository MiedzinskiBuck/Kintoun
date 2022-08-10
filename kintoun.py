import argparse
from functions import banner, change_agent, credential_handler
from colorama import Fore, Style

class Program:
    def __init__(self, args):
        self.args = args
        self.user_agent = self.args.user_agent
        self.profile = self.args.profile
        self.config()

    def config(self):
        if self.user_agent == None:
            self.botoconfig = change_agent.Agent()

    def run(self):
        print("On Run function")
        print(self.botoconfig)
        print(self.args.arguments)

    def console(self):
        print("On Console function")
        profile = credential_handler.Credential(self.profile)
        

if __name__ == '__main__':
    banner.Banner()

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--user-agent', '-u')
    parent_parser.add_argument('--profile', '-p', nargs='?', const='default')
    parent_parser.add_argument('--access-key')
    parent_parser.add_argument('--secret-access-key')

    #parent_parser.add_argument('--argument', '-a', type=argparse.FileType('r'))     // In case I need to load a wordlist
    #parent_parser.add_argument('--argument', '-a', default='DefaultValue')     // In case I need to set a default value for an argument

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(title='commands', dest='command')

    module_parser = subparser.add_parser('run', help='Run the selected module', parents = [parent_parser])
    module_parser.add_argument('--module', '-m', help='Select a module to run', required=True)
    module_parser.add_argument('--arguments', '-a', help='Module arguments')

    console_parser = subparser.add_parser('console', help='Create a console link', parents = [parent_parser])
    
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit()
    
    p = Program(args)

    if args.command == 'run':
        p.run()
    elif args.command == 'console':
        p.console()

