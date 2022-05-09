import boto3
import botocore.exceptions
from colorama import Fore, Style
from functions import create_client
from functions import region_parser

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will use the results of the 'enumeration\cloudformation_enumerate_stacks'")
    print("\tmodule to describe the stack's template.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will give you a list of available stacks. Select the desired template to")
    print("\tview or 'All' to describe all templates. The results will be save on the 'results' folder.")

def create_cloudformation_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, "cloudformation", region)
    return client.create_aws_client()

def get_stack_information_enumeration_results():
    pass

def get_stack_template():
    pass

def main(botoconfig, session, selected_session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting CloudFormation Describe Templates module...")
    pass