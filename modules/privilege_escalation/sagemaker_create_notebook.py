import json
import sys
from sympy import EX
import boto3
import datetime 
from dateutil.tz import tzutc
from colorama import Fore, Style
from modules.enumeration import iam_enumerate_assume_role

def create_client(botoconfig, session, service):
    client = session.client(service, config=botoconfig)
    return client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\t")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def check_permissions(selected_session):
    try:
        permission_results_file = "./results/{}_session_data/iam/iam_enumerate_permissions_results.json".format(selected_session)
        results_file = open(permission_results_file, "r").read()
    except:
        print(Fore.RED + "[-] No permission results found...make sure to run the 'iam_enumerate_permissions' module to enumerate permissions..." + Style.RESET_ALL)
        return False

    if "sagemaker:CreateNotebookInstance" in results_file and "sagemaker:CreatePresignedNotebookInstanceUrl" in results_file and "iam:PassRole" in results_file:
        return True
    else:
        return False 

def check_assumable_roles(botoconfig, session, selected_session):
    service = 'iam'
    client = create_client(botoconfig, session, service)
    assumable_roles = iam_enumerate_assume_role.get_assumable_roles(client)

    sage_maker_assumable_roles = []
    
    for role in assumable_roles:
        try:
            if role['AssumeRolePolicyDocument']:
                for principal in role['AssumeRolePolicyDocument']['Statement']:
                    if principal['Principal']['Service'] == 'lambda.amazonaws.com':
                        sage_maker_assumable_roles.append(role['Arn'])
        except:
            next
    
    return sage_maker_assumable_roles

def parse_assumable_role_option(role_list):
    if role_list:
        print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
        print("[+] Select Role:")
        option = 0
        role_options = {}
        for role in role_list:
            role = role.split("_")[0]
            role_options[str(option)] = role 
            print("{} - {}".format(str(option), role))
            option += 1
        selected_option = input("\nOption: ")
        if not selected_option or selected_option not in role_options:
            print("\n[-] No valid role selected...exiting...")
            return False
        selected_option = int(selected_option)
        role_name = role_options[str(selected_option)]
    else:
        print("NO ROLE TO SELECT")

    print(role_name)

def create_notebook():
    # We create a notebook and pass the selected role to it
    pass

def create_presigned_url():
    # We create a presigned url to access the notebook from the browser. Maybe this will be deprecated if I can automate this process without the browser.
    pass

def get_jupyter_credentials():
    # We use the notebooks terminal to get temporary credentials
    pass

def main(botoconfig, session, selected_session):
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
    print("[+] Starting SageMaker privilege escalation module...")
    print("[+] Checking for required permissions...")

    required_permissions = check_permissions(selected_session)

    if not required_permissions:
        option = input("\n[-] KintoUn was not able to identity the required permissions...do you want to continue executing the module? [y/N]: ")
        if not option or option.lower() == "n":
            print("[-] Exiting module...")
            return 
    else:
        print("[+] Permissions Found! Cheking Assumable Roles...")
    
    assumable_roles = check_assumable_roles(botoconfig, session, selected_session)
    attack_role = parse_assumable_role_option(assumable_roles)