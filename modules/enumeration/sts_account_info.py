from colorama import Fore, Style
from functions import sts_handler

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate information about the account.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def main(botoconfig, session):
    print("\n[+] Getting account information...")
    print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
    sts = sts_handler.STS(botoconfig, session)

    account_info = sts.get_caller_identity()
    print("Account Number: "+Fore.GREEN+"{}".format(account_info['Account'])+Style.RESET_ALL)
    print("User Arn: "+Fore.GREEN+"{}".format(account_info['Arn'])+Style.RESET_ALL)

    return account_info
    