import boto3
from colorama import Fore, Style

def get_user_name(session):
    client = session.client('iam')
    username = client.get_user()['User']['UserName']

    return username

def main(selected_session, session):
    print("\n[+] Getting user name....")
    current_user = {}
    username = get_user_name(session)

    current_user['current_user'] = username

    print(Fore.GREEN + "\n[+] Current User: " + Style.RESET_ALL + "{}".format(current_user['current_user']))

    return current_user