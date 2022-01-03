import boto3
from colorama import Fore, Style

def create_client(botoconfig, session):
    client = session.client('iam', config=botoconfig)

    return client

def get_user_name(botoconfig, session):
    client = create_client(botoconfig, session)
    username = client.get_user()['User']['UserName']

    return username

def main(botoconfig, session):
    print("\n[+] Getting user name....")
    current_user = {}
    username = get_user_name(botoconfig, session)

    current_user['current_user'] = username

    print(Fore.GREEN + "\n[+] Current User: " + Style.RESET_ALL + "{}".format(current_user['current_user']))

    return current_user