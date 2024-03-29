# WORK IN PROGRESS

import boto3
from colorama import Fore, Style

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\t")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def permissions_enumeration_check():
    try:
        permission_results_file = "./results/{}_session_data/iam/iam_enumerate_permissions_results.json".format()
        results_file = open(permission_results_file, "r").read()
        return results_file
    except:
        return False

def administrator_check(enumerated_permissions): 
    if '{"Effect": "Allow", "Action": "*", "Resource": "*"}' in enumerated_permissions:
        return True

def sagemaker_create_notebook_check(enumerated_permissions):
    if "sagemaker:CreateNotebookInstance" in enumerated_permissions and "sagemaker:CreatePresignedNotebookInstanceUrl" in enumerated_permissions and "iam:PassRole" in enumerated_permissions:
        return True

def sagemaker_notebook_abuse_check(enumerated_permissions):
    if "sagemaker:ListNotebookInstances" in enumerated_permissions and "sagemaker:CreatePresignedNotebookInstanceUrl" in enumerated_permissions:
        return True

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting privilege escalation scan module...\n")

    check_for_admin = administrator_check(permissions_file)
    if check_for_admin:
        print("* "+Fore.GREEN+"User Already Administrator!"+Style.RESET_ALL)
        return 

    sage_create_notebook = sagemaker_create_notebook_check(permissions_file)
    if sage_create_notebook:
        print("* PrivEsc Module Suggestion: "+Fore.GREEN+"{}".format("privilege_escalation/sagemaker_create_notebook")+Style.RESET_ALL)

    sage_abuse_notebook = sagemaker_create_notebook_check(permissions_file)
    if sage_abuse_notebook:
        print("* PrivEsc Module Suggestion: "+Fore.GREEN+"{}".format("privilege_escalation/sagemaker_notebook_abuse")+Style.RESET_ALL)