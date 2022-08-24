import boto3
from colorama import Fore, Style
from functions import create_client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate existing users on the account.")
    print("\tIt will print the 'UserName' and 'Arn' of the found users.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def create_iam_client(botoconfig, session):
    client = create_client.Client(botoconfig, session, 'iam')
    return client.create_aws_client()

def iam_enumerate_users(botoconfig, session):
    client = create_iam_client(botoconfig, session)
    response = client.list_users()

    return response

def main(botoconfig, session):
    users = iam_enumerate_users(botoconfig, session)
    for user in users["Users"]:
        print(Fore.GREEN + "\n[+] UserName: " + Style.RESET_ALL + "{}".format(user["UserName"]))
        print(Fore.GREEN + "[+] Arn: " + Style.RESET_ALL + "{}".format(user["Arn"]))

    return users