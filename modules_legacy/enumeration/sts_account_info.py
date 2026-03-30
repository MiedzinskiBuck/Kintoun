MODULE_METADATA = {
    'name': 'sts_account_info',
    'display_name': 'Sts Account Info',
    'category': 'enumeration',
    'description': 'Return account and ARN details from STS caller identity.',
    'requires_region': False,
    'inputs': [],
    'output_type': 'json',
    'risk_level': 'low'
}
from functions.no_color import Fore, Style
from functions import sts_handler, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate information about the account.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_sts_client(botoconfig, session):
    return sts_handler.STS(botoconfig, session)

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

    return utils.module_result(data=account_info)
    




