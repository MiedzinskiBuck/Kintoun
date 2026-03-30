import botocore.exceptions
from functions.no_color import Fore, Style
from functions import Cloudformation_handler, region_parser, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate existing stacks and their status on the given region. To do")
    print("\tthis, use the 'enumeration\cloudformation_describe_templates' module.\n")

    print("[+] Module Functionality:\n")
    print("\tJust run the module and inform the region to list the stacks.")

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region 

def list_stacks(botoconfig, session, region):
    stack_list = []

    try:
        print("[+] Enumerating Stacks in {}".format(region))
        cloudformation = Cloudformation_handler.Cloudformation(botoconfig, session, region)
        stack_data = cloudformation.list_stacks()
        if not stack_data:
            return stack_list
        stack_list.append(stack_data)

        while stack_data.get('NextToken'):
            stack_data = cloudformation.list_stacks(stack_data['NextToken'])
            if not stack_data:
                break
            stack_list.append(stack_data)
                            
        return stack_list

    except botocore.exceptions.ClientError as e:
        print(Fore.RED + str(e) + Style.RESET_ALL)
    pass

def parse_stack_information(stack_list):
    if not stack_list:
        return
    for stack in stack_list[0]:
        for summary in stack['StackSummaries']:
            print("\t[+] Stack ID = {}".format(summary['StackId']))
            print("\t[+] Stack Name = {}".format(summary['StackName']))
            if summary['StackStatus'] == "CREATE_COMPLETE":
                print("\t[+] Stack Status = "+Fore.GREEN+"{}\n".format(summary['StackStatus']) + Style.RESET_ALL)
            else:
                print("\t[+] Stack Status = "+Fore.YELLOW+"{}\n".format(summary['StackStatus']) + Style.RESET_ALL)

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting CloudFormation Stack Enumeration module...")
    print("[+] Select region to retrieve stacks...")

    cloudformation_stack_data = []

    region_option = get_optional_regions()

    if region_option:
        for region in region_option:
            instance_data = list_stacks(botoconfig, session, region)
            if instance_data:
                cloudformation_stack_data.append(instance_data)
    
    parse_stack_information(cloudformation_stack_data)

    return utils.module_result(data=cloudformation_stack_data)
