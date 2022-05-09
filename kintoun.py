import boto3, sys, readline
from functions import banner, data_parser, module_handler, command_handler, change_agent, completer
from colorama import Fore, Style
from botocore.exceptions import ProfileNotFound

def main():
    available_commands = ['modules', 'exit', 'use', 'help', 'run', 'results']

    banner.Banner()
    module_action = module_handler.Modules()
    parser = data_parser.Parser()

    comp = completer.Completer()

    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(comp.complete)

    botoconfig = change_agent.Agent()

    try:
        selected_session = parser.session_select()

        profile = input("\n[+] Profile to be used: ")

        if not profile:
            profile = "default"

        try:
            session = boto3.Session(profile_name=profile)
        except ProfileNotFound:
            print("[-] Profile not found... exiting...")
            sys.exit()

        print("\n[+] Using profile: " + Fore.GREEN + "{}\n".format(profile) + Style.RESET_ALL)
        print("[+] Ready to begin! Type 'modules' for a list of available modules.")
        print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

        while True:
            try:
                cmd = input("\nKintoUn = [{}:{}] $ ".format(selected_session, profile))
                check_cmd = cmd.lower().split()

                if check_cmd[0] == "modules":
                    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
                    print(Fore.YELLOW + "AVAILABLE MODULES" + Style.RESET_ALL)
                    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
                    module_action.list_available_modules()

                elif check_cmd[0] == "commands":
                    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
                    print(Fore.YELLOW + "AVAILABLE COMMANDS" + Style.RESET_ALL)
                    print(Fore.YELLOW + "================================================================================================\n" + Style.RESET_ALL)
                    command_handler.Commands(available_commands)

                elif check_cmd[0] == "results":
                    print("[-] Module not yet implemented...you can use 'cat' to see the module's results at the 'results' folder...")
                    #print("\n[+] Fetching results...")
                    #parser.fetch_results(selected_session)

                elif check_cmd[0] == "exit":
                    print("\nGoodbye!")
                    break

                elif check_cmd[1] == "use" or check_cmd[1] == "run":
                    module_results = module_action.load_module(cmd, botoconfig, session, selected_session)
                    if module_results == None:
                        pass
                    else:
                        try:
                            executed_module = cmd.lower().split()[0]
                            parsed_module_results = parser.parse_module_results(executed_module, module_results)
                            parser.store_parsed_results(selected_session, executed_module, parsed_module_results)
                        except Exception as e:
                            print("[-] Failed to store results: {}".format(e))

                elif check_cmd[1] == "help":
                    module_action.module_help(cmd)

                else:
                    print("\n[-] Unavailable command.")

            except Exception as e:
                print(e)

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()
