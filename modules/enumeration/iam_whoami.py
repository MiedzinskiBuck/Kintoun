import boto3
from functions import create_client
from colorama import Fore, Style

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate the current user profile.")
    print("\tIt will print the 'CurrentUser' information.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
    
def get_user_name(botoconfig, session):
    client = create_client.Client(botoconfig, session, 'iam')
    iam_client = client.create_aws_client()
    username = iam_client.get_user()['User']['UserName']

    return username

def main(botoconfig, session, selected_session):
    print("\n[+] Getting user name....")
    current_user = {}
    username = get_user_name(botoconfig, session)

    current_user['current_user'] = username

    print("[+] Current User: "+Fore.GREEN+"{}".format(current_user['current_user'])+Style.RESET_ALL)

    return current_user