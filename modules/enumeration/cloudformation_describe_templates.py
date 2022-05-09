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

def get_stack_information_enumeration_results(selected_session):
    try:
        permission_results_file = "./results/{}_session_data/cloudformation/cloudformation_enumerate_stacks_results.json".format(selected_session)
        results_file = open(permission_results_file, "r")
        return json.load(results_file)
    except:
        return False

def get_stack_template(cloudformation_client, stack_id):
    try:
        response = cloudformation_client.get_template(
            StackName=stack_id
            )

        return response
    except:
        return False
    
def main(botoconfig, session, selected_session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting CloudFormation Describe Templates module...")
    print("[+] Retrieving Stack information results...")

    stacks_templates = []

    results_file = get_stack_information_enumeration_results(selected_session)

    if not results_file:
        print("[-] "+Fore.RED+"No stack enumeration results found"+Style.RESET_ALL+"...make sure to run the 'cloudformation_enumerate_stacks' module to enumerate stack data...")
        return False 
    
    print("[+] Retrieving Stacks Template...")

    total_templates = []

    for stack_data in results_file['cloudformation']:
        for stack_summary in stack_data[0]['StackSummaries']:
            total_templates.append(stack_summary['StackName'])

    print("\n[+] There are "+Fore.YELLOW+"{}".format(len(total_templates))+Style.RESET_ALL+" templates available...")
    option = input("Do you want to retrieve the template of all of them? [y/N]: ")

    try:
        if not option or option.lower() == 'n':
            for stack_data in results_file['cloudformation']:
                for stack_summary in stack_data[0]['StackSummaries']:
                    print("- {}".format(stack_summary['StackId']))
            stack_id = input("Please select the template to retrieve: ")
            region = stack_id.split(":")[3]
            cloudformation_client = create_cloudformation_client(botoconfig, session, region)
            template = get_stack_template(cloudformation_client, stack_id)
            stacks_templates.append(template)
        elif option.lower() == 'y':
            for stack_data in results_file['cloudformation']:
                for stack_summary in stack_data[0]['StackSummaries']:
                    print("[+] Retrieving Template for "+Fore.GREEN+"{}".format(stack_summary['StackName']+Style.RESET_ALL))
                    stack_id = stack_summary['StackId']
                    region = stack_summary['StackId'].split(":")[3]
                    cloudformation_client = create_cloudformation_client(botoconfig, session, region)
                    template = get_stack_template(cloudformation_client, stack_id)
                    stacks_templates.append(template)
        else:
            print("[-]Please provide a valid option...exiting...")

        print("\n[+] Done! Results are saved on 'results/{}_session_data/cloudformation/cloudformation_describe_templates_results.json'".format(selected_session))

    except Exception as e:
        print(e)


    return stacks_templates