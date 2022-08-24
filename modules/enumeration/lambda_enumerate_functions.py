import boto3
from colorama import Fore, Style
from functions import create_client
from functions import region_parser

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate lambda functions from a given region.")
    print("\tIt will print the ARN of those functions and store its details on the results folder.")

    print("[+] Module Functionality:\n")
    print("\tJust run the module and select which region you want to enumerate.")

def create_lambda_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, 'lambda', region)

    return client.create_aws_client()

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region

def get_lambda_function_list(botosession, session, region):
    lambda_client = create_lambda_client(botosession, session, region)
    response = lambda_client.list_functions()

    return response

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
                if lambda_functions['Functions'] == []:
                    pass
                else:
                    for function in lambda_functions['Functions']:
                        print("[+] Function Arn: "+Fore.GREEN+"{}".format(function['FunctionArn'])+Style.RESET_ALL)
                        lambda_function_list.append(function)
            except:
                pass
    
    return lambda_function_list 