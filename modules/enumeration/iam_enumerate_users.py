import boto3
from colorama import Fore, Style

def iam_enumerate_users(session):
    client = session.client('iam')
    response = client.list_users()

    return response

def main(selected_session, session):
    users = iam_enumerate_users(session)
    for user in users["Users"]:
        print(Fore.GREEN + "\n[+] UserName: " + Style.RESET_ALL + "{}".format(user["UserName"]))
        print(Fore.GREEN + "[+] Arn: " + Style.RESET_ALL + "{}".format(user["Arn"]))

    return users