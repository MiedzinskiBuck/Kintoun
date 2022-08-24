import boto3
import botocore.exceptions
import json

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

    print("[+] IMPORTANT:\n")
    print("\tResults for this module could be lenghty, so it won't print them to the screen...")
    print("\tYou can see them on the 'results' directory that will be showned on screen...")

def create_cloudformation_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, "cloudformation", region)
    return client.create_aws_client()

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region 

def get_stack_template(cloudformation_client, stack_id):
    try:
        response = cloudformation_client.get_template(
            StackName=stack_id
            )

        return response
    except:
        return False
    
def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting CloudFormation Describe Templates module...")

    print("[+] Retrieving Stacks Template...")

    stack_id = input("Stack Arn: ")
    region = stack_id.split(":")[3]

    cloudformation_client = create_cloudformation_client(botoconfig, session, region)

    stack_template = get_stack_template(cloudformation_client, stack_id)
    print(json.dumps(stack_template, indent=4))

    return stack_template