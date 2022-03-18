import boto3
from colorama import Fore, Style
from modules.enumeration import iam_enumerate_permissions

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate the assume role policy for the existing roles.")
    print("\tIt will take advantage os the 'iam_enumerate_permissions' module.\n")

    print("\tTo function, the module will load the 'iam_enumerate_permissions.get_account_information'")
    print("\tand use the 'role_details' results to enumerate available roles.")
    print("\tWith the available roles, it will enumerate the 'AssumeRolePolicyDocument' and show")
    print("\twhich principal can enumerate which role...")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def create_client(botoconfig, session):
    client = session.client('iam', config=botoconfig)
    return client

def get_assumable_roles(client):
    user_details, group_details, role_details, policy_details = iam_enumerate_permissions.get_account_information(client)
    return role_details

def parse_results(role_details):
    for role in role_details:
        if role['AssumeRolePolicyDocument']:
            print("\n[+] Role " + Fore.GREEN + "{}".format(role['Arn']) + Style.RESET_ALL + " can be assumed by:")
            for principal in role['AssumeRolePolicyDocument']['Statement']:
                print(Fore.YELLOW + "\t{}".format(principal['Principal']) + Style.RESET_ALL)
    
def main(botoconfig, session, selected_session):
    print("\n[+] Starting enumeration of Assume Role Policies on the account...")
    client = create_client(botoconfig, session)
    assumable_roles = get_assumable_roles(client)

    print("[+] Parsing results...")

    parse_results(assumable_roles)

    role_results = {}

    for role in assumable_roles:
        if role['AssumeRolePolicyDocument']:
            for principal in role['AssumeRolePolicyDocument']['Statement']:
                role_results[role['Arn']] = principal['Principal']

    return role_results