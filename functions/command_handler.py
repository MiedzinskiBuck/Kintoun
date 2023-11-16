from colorama import Fore, Style

class Commands:

    """"This is a very simple class to print KintoUn's available commands"""

    def __init__(self, available_commands):
       for command in available_commands:
            print("- {}".format(command))