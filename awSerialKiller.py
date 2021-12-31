import boto3
import sys
import os
import importlib
from functions import banner
from functions import data_parser
from botocore.exceptions import ProfileNotFound

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

    try:
        while True:
            try:
                cmd = input("\nAWSerialKiller = [{}:{}] -> ".format(selected_session, profile))
                check_cmd = cmd.lower().split()[0]

                if check_cmd not in available_commands:
                    print("\n[-] Unavailable module, type 'modules' for a list of available modules.")

                elif check_cmd == "modules":
                    available_modules = list_available_modules()
                    print("\n==============================\nAVAILABLE MODULES\n==============================")
                    for module_category in available_modules:
                        print("\n{}\n".format(module_category.upper()))
                        for module in available_modules[module_category]:
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
                    print("\n==============================\nAVAILABLE COMMANDS\n==============================")
                    for command in available_commands:
                        print("- {}".format(command))
            except Exception as e:
                print(e)

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()