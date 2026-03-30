import botocore
from functions.no_color import Fore, Style
from functions import lambda_handler, region_parser, utils

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate lambda functions from a given region.")
    print("\tIt will print the ARN of those functions and store its details on the results folder.")

    print("[+] Module Functionality:\n")
    print("\tJust run the module and select which region you want to enumerate.")

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region

def get_lambda_function_list(botosession, session, region):
    lambda_client = lambda_handler.Lambda(botosession, session, region)
    return lambda_client.list_functions()

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting Lambda Function Enumeration module...")
    print("[+] Select region to retrieve functions...")
    
    lambda_function_list = []

    region_option = get_optional_regions()

    if region_option:
        for region in region_option:
            print("[+] Enumerating lambda functions for "+Fore.YELLOW+"{}".format(region)+Style.RESET_ALL+"....")
            try:
                lambda_functions = get_lambda_function_list(botoconfig, session, region)
                if lambda_functions and lambda_functions.get('Functions'):
                    for function in lambda_functions['Functions']:
                        print("[+] Function Arn: "+Fore.GREEN+"{}".format(function['FunctionArn'])+Style.RESET_ALL)
                        lambda_function_list.append(function)
            except botocore.exceptions.ClientError as e:
                print(Fore.RED + f"[-] Failed to enumerate Lambda in {region}: {e}" + Style.RESET_ALL)
    
    return utils.module_result(data=lambda_function_list)
