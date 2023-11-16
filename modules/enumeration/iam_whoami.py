from functions import iam_handler 
from colorama import Fore, Style

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate the current user profile.")
    print("\tIt will print the 'CurrentUser' information.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    print("\n[+] Getting user name....")
    username = iam.whoami()
    print("[+] Current User: "+Fore.GREEN+"{}".format(username)+Style.RESET_ALL)

    return username