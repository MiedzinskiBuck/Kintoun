import botocore.exceptions
import json

from functions.no_color import Fore, Style
from functions import Cloudformation_handler, region_parser, utils

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

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region 

def get_stack_template(cloudformation, stack_id):
    try:
        response = cloudformation.get_template(stack_id)
        return response
    except botocore.exceptions.ClientError:
        return False


def collect_inputs():
    stack_id = input("Stack Arn: ")
    return stack_id
    
def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting CloudFormation Describe Templates module...")

    print("[+] Retrieving Stacks Template...")

    stack_id = collect_inputs()
    region = stack_id.split(":")[3]

    cloudformation = Cloudformation_handler.Cloudformation(botoconfig, session, region)

    stack_template = get_stack_template(cloudformation, stack_id)
    print(json.dumps(stack_template, indent=4))

    return utils.module_result(data=stack_template)
