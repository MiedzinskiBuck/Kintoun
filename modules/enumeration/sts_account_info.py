import boto3
from colorama import Fore, Style
from functions import create_client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate information about the account.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_sts_client(botoconfig, session):
    client = create_client.Client(botoconfig, session, 'sts')
    return client.create_aws_client()

def get_account_info(client):
    response = client.get_caller_identity()
    return response

def main(botoconfig, session):
    print("\n[+] Getting account information...")
    print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)

    sts_client = get_sts_client(botoconfig, session)

    account_info = get_account_info(sts_client)
    print("Account Number: "+Fore.GREEN+"{}".format(account_info['Account'])+Style.RESET_ALL)
    print("User Arn: "+Fore.GREEN+"{}".format(account_info['Arn'])+Style.RESET_ALL)

    return account_info
    