import boto3
from colorama import Fore, Style
from functions import create_client

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\t")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

# The main function will orchestrate the functionality of the module. The idea is that it will call whatever needs calling and returns the results from the module to be parsed and stored.
# It will be called from the main program with the botoconfig, that changes the user agent, and the session, which stores the profile credentials to be used.
def main(botoconfig, session, selected_session):
    # module code, calls, etc...
    # return module_results
    pass