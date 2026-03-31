MODULE_METADATA = {
    'name': 'iam_enumerate_users',
    'display_name': 'Iam Enumerate Users',
    'category': 'enumeration',
    'description': 'Enumerate IAM users in the target account.',
    'requires_region': False,
    'inputs': [],
    'output_type': 'json',
    'risk_level': 'low'
}
from functions.no_color import Fore, Style
from functions import iam_handler

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate existing users on the account.")
    print("\tIt will print the 'UserName' and 'Arn' of the found users.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    users = iam.enumerate_users()
    for user in users["Users"]:
        print("\n[+] UserName: " + Fore.GREEN + "{}".format(user["UserName"] + Style.RESET_ALL))
        print("[+] Arn: " + Fore.GREEN + "{}".format(user["Arn"] + Style.RESET_ALL))

    return users




