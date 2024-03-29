import boto3
from colorama import Fore, Style
from functions import region_parser
from functions import create_client

def create_ssm_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, 'ssm', region)
    return client.create_aws_client()

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate existing parameters on")
    print("\tsystem manager. If they exists, it will print them")
    print("\ton screen and stores the parameter details on the results")
    print("\tfolder")

    print("[+] Module Functionality:\n")
    print("\tThe module will ask on what region do you want to")
    print("\trun it. The default option runs the module on all regions.")

    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region 

def list_ssm_parameters(botoconfig, session, region):
    ssm_client = create_ssm_client(botoconfig, session, region)
    response = ssm_client.describe_parameters() 

    return response, ssm_client

def get_parameter_value(ssm_client, parameter_name):
    response = ssm_client.get_parameter(
        Name=parameter_name,
        WithDecryption=True
    )
    
    return response

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting Systems Manager Parameters enumeration module...")
    print("[+] Select region to retrieve parameters...")

    found_parameters = []

    region_option = get_optional_regions()
    if region_option:
        for region in region_option:
            print("[+] Enumerating parameters for "+Fore.YELLOW+"{}".format(region)+Style.RESET_ALL+"...")
            try:
                ssm_parameters, ssm_client = list_ssm_parameters(botoconfig, session, region)
                if ssm_parameters['Parameters'] == []:
                    pass
                else:
                    for parameter in ssm_parameters['Parameters']:
                        print("[+] Parameter: "+Fore.GREEN+"{}".format(parameter['Name'])+Style.RESET_ALL)
                        parameter_value = get_parameter_value(ssm_client, parameter['Name'])
                        print("{}".format(parameter_value['Parameter']['Value']))
                        found_parameters.append(parameter_value)
            except:
                pass
    
    return found_parameters