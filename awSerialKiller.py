import boto3
import sys
from functions import banner
from functions import data_parser
from functions import module_handler
from functions import command_handler
from botocore.exceptions import ProfileNotFound
from colorama import Fore, Style

def main():
    available_commands = ['modules', 'exit', 'use', 'help', 'run']

    banner.Banner()
    module_action = module_handler.Modules()
    command_action = command_handler.Commands()
    parser = data_parser.Parser()

    selected_session = parser.session_select()

    profile = input("[+] Profile to be used: ")

    if not profile:
        profile = "default"

    try:
        session = boto3.Session(profile_name=profile)
    except ProfileNotFound:
        print("[-] Profile not found... exiting...")
        sys.exit()

    print("\n[+] Using profile: {}\n".format(profile))
    print("[+] Ready to begin! Type 'modules' for a list of available modules.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

    try:
        while True:
            try:
                cmd = input("\nAWSerialKiller = [{}:{}] $ ".format(selected_session, profile))
                check_cmd = cmd.lower().split()[0]

                if check_cmd not in available_commands:
                    print("\n[-] Unavailable command, type 'help' for a list of available commands.")

                elif check_cmd == "modules":
                    module_action.list_available_modules()
                            
                elif check_cmd == "exit":
                    print("\nGoodbye!")
                    break

                elif check_cmd == "use" or check_cmd == "run":
                    module_results = module_action.load_module(cmd, selected_session, session)
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
                    command_action.list_available_commands(available_commands)
            except Exception as e:
                print(e)

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()