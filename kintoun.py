import argparse
import importlib
import os
from functions import banner, change_agent, credential_handler
from colorama import Fore, Style

class Program:
    def __init__(self, args):
        self.args = args
        self.user_agent = self.args.user_agent
        self.profile = self.args.profile
        self.aws_access_key_id = self.args.access_key
        self.aws_secret_access_key = self.args.secret_access_key
        self.aws_session_token = self.args.session_token
        self.config()

    def config(self):
        if self.user_agent == None:
            self.botoconfig = change_agent.Agent()

    def parseCredentials(self):
        provided_credentials = {
            "aws_access_key_id": self.aws_access_key_id, 
            "aws_secret_access_key": self.aws_secret_access_key, 
            "aws_session_token": self.aws_session_token, 
            "profile": self.profile
        }
        credentials = credential_handler.Credential(provided_credentials)

        return credentials.session

    def run(self):
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
        print("Running "+Fore.GREEN+f"/{self.args.category}/{self.args.module}"+Style.RESET_ALL+" module...")
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)

        session = self.parseCredentials()
        try:
            module_path = f"modules/{self.args.category}/{self.args.module}"
            module_path = module_path.replace('/', '.').replace('\\', '.')
            module = importlib.import_module(module_path)
            self.module_info = module.main(self.botoconfig, session)

        except ModuleNotFoundError:
            raise ModuleNotFoundError("\n[-] Module not found...Type 'modules' for a list of available modules...")

    def console(self):
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
        print("Creating console link...")
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)

        session = self.parseCredentials()
        console_module_path = "modules.misc.console"
        console_module = importlib.import_module(console_module_path)
        self.module_info = console_module.main(self.botoconfig, session)
    
    def list_modules(self):
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
        print("Listing available modules...")
        print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)

        catalog = {}
        categories = os.listdir("./modules/")
        for category in categories:
            try:
                modules = os.listdir("./modules/{}/".format(category))
                catalog[category] = modules
            except NotADirectoryError:
                pass

        for module_category in catalog:
            if module_category.upper() == "__PYCACHE__" or module_category.upper() == "__INIT__":
                pass
            else:
                print(Fore.GREEN + "\n{}\n".format(module_category.upper()) + Style.RESET_ALL)
                for module in catalog[module_category]:
                    if module.upper() == "__PYCACHE__" or module.strip(".py").upper() == "__INIT__":
                        pass
                    else:
                        print("- {}/{}".format(module_category, module.strip(".py")))

if __name__ == '__main__':
    banner.Banner()

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--user-agent', '-u')
    parent_parser.add_argument('--profile', '-p', nargs='?', const='default')
    parent_parser.add_argument('--environment', '-e', nargs='?')
    parent_parser.add_argument('--access-key')
    parent_parser.add_argument('--secret-access-key')
    parent_parser.add_argument('--session-token')

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(title='commands', dest='command')

    module_parser = subparser.add_parser('run', help='Run the selected module', parents = [parent_parser])
    module_parser.add_argument('--category', '-c', help='Select a category to run', required=True)
    module_parser.add_argument('--module', '-m', help='Select a module to run', required=True)
    module_parser.add_argument('--arguments', '-a', help='Module arguments')

    console_parser = subparser.add_parser('console', help='Create a console link', parents = [parent_parser])
    list_parser = subparser.add_parser('list', help='List available Modules', parents = [parent_parser])
    
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        exit()
    
    p = Program(args)

    if args.command == 'run':
        p.run()
    elif args.command == 'console':
        p.console()
    elif args.command == 'list':
        p.list_modules()