import boto3
from colorama import Fore, Style

def create_client(botoconfig, session):
    client = session.client('iam', config=botoconfig)

    return client

def iam_enumerate_users(botoconfig, session):
    client = create_client(botoconfig, session)
    response = client.list_users()

    return response

def main(botoconfig, session):
    users = iam_enumerate_users(botoconfig, session)
    for user in users["Users"]:
        print(Fore.GREEN + "\n[+] UserName: " + Style.RESET_ALL + "{}".format(user["UserName"]))
        print(Fore.GREEN + "[+] Arn: " + Style.RESET_ALL + "{}".format(user["Arn"]))

    return users