import boto3
import sys
import os
import importlib
from functions import banner
from functions import data_parser
from botocore.exceptions import ProfileNotFound
from colorama import Fore, Style

def list_available_modules():
    catalog = {}
    categories = os.listdir("./modules/")
    for category in categories:
        try:
            modules = os.listdir("./modules/{}/".format(category))
            catalog[category] = modules
        except NotADirectoryError:
            pass
    
    return catalog

def load_module(cmd, selected_session, session):
    cmd_arguments = cmd.split()

    try:
        module_path = "modules/{}".format(cmd_arguments[1])
        module_path = module_path.replace('/', '.').replace('\\', '.')

        module = importlib.import_module(module_path)
        module_info = module.main(selected_session, session)

        return module_info

    except ModuleNotFoundError:
        print("\n[-] Module not found...\n[-] Type 'modules' for a list of available modules...")

def main():
    banner.Banner()
    parser = data_parser.Parser()

    available_commands = ['modules', 'exit', 'use', 'help', 'run']
    selected_session = parser.session_select()

    profile = input("\n[+] Profile to be used: ")

    if not profile:
        profile = "default"

    try:
        session = boto3.Session(profile_name=profile)
    except ProfileNotFound:
        print("[-] Profile not found... exiting...")
        sys.exit()

    print("[+] Using profile: {}\n".format(profile))
    print("[+] Ready to begin! Type 'modules' for a list of available modules.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

    try:
        while True:
            try:
                cmd = input("\nAWSerialKiller = [{}:{}] $ ".format(selected_session, profile))
                check_cmd = cmd.lower().split()[0]

                if check_cmd not in available_commands:
                    print("\n[-] Unavailable module, type 'modules' for a list of available modules.")

                elif check_cmd == "modules":
                    available_modules = list_available_modules()
                    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
                    print(Fore.YELLOW + "AVAILABLE MODULES" + Style.RESET_ALL)
                    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
                    for module_category in available_modules:
                        if module_category.upper() == "__PYCACHE__" or module_category.upper() == "__INIT__":
                            pass
                        else:
                            print(Fore.GREEN + "\n{}\n".format(module_category.upper()) + Style.RESET_ALL)
                            for module in available_modules[module_category]:
                                if module.upper() == "__PYCACHE__" or module.strip(".py").upper() == "__INIT__":
                                    pass
                                else:
                                    print("- {}/{}".format(module_category, module.strip(".py")))
                            
                elif check_cmd == "exit":
                    print("\nGoodbye!")
                    break

                elif check_cmd == "use" or check_cmd == "run":
                    module_results = load_module(cmd, selected_session, session)
                    if module_results == None:
                        pass
                    else:
                        try:
                            executed_module = cmd.lower().split()[1]
                            parsed_module_results = parser.parse_module_results(executed_module, module_results)
                            parser.store_parsed_results(selected_session, executed_module, parsed_module_results)
                        except Exception as e:
                            print("[-] Failed to store results: {}".format(e))

                elif check_cmd == "help":
                    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
                    print(Fore.YELLOW + "AVAILABLE COMMANDS" + Style.RESET_ALL)
                    print(Fore.YELLOW + "================================================================================================\n" + Style.RESET_ALL)
                    for command in available_commands:
                        print("- {}".format(command))
            except Exception as e:
                print(e)

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()