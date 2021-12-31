from colorama import Fore, Style

class Commands:

    def list_available_commands(self, available_commands):
        print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
        print(Fore.YELLOW + "AVAILABLE COMMANDS" + Style.RESET_ALL)
        print(Fore.YELLOW + "================================================================================================\n" + Style.RESET_ALL)
        for command in available_commands:
            print("- {}".format(command))