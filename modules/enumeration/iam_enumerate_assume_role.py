import boto3
from colorama import Fore, Style
from modules.enumeration import iam_enumerate_permissions

def create_client(botoconfig, session):
    client = session.client('iam', config=botoconfig)
    return client

def help():
    print("[+] This module will enumerate the assume role policy for the existing roles.")
    print("[+] It will take advantage os the 'iam_enumerate_permissions' module.")

def main(botoconfig, session):
    print("\n[+] Starting enumeration of Assume Role Policies on the account...")
    client = create_client(botoconfig, session)
    user_details, group_details, role_details, policy_details = iam_enumerate_permissions.get_account_information(client)
    print("[+] Parsing results...")

    role_results = {}

    for role in role_details:
        if role['AssumeRolePolicyDocument']:
            print("\n[+] Role " + Fore.GREEN + "{}".format(role['Arn']) + Style.RESET_ALL + " can be assumed by:")
            for principal in role['AssumeRolePolicyDocument']['Statement']:
                print(Fore.YELLOW + "\t{}".format(principal['Principal']) + Style.RESET_ALL)
                role_results[role['Arn']] = principal['Principal']

    return role_results