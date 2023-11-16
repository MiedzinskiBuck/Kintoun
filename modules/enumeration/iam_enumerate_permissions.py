import json 
from colorama import Fore, Style
from functions import iam_handler
from functions import utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate permissions for the current user.")
    print("\tIt will gather information about roles, inline policies, groups and attached policies.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    print("\n[+] Starting Permissions Enumeration for current user...")

    user_details, group_details, role_details, policy_details = iam.get_account_information()
    username = iam.whoami()
    policy_documents = utils.parse_account_information(username, user_details, group_details, role_details, policy_details)

    print("[+] Permission Set...")
    print(json.dumps(policy_documents, indent=4, default=str))

    return policy_documents