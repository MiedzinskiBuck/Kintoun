import boto3
import json
from colorama import Fore, Style
from functions import create_client

def create_ec2_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, 'ec2', region)
    return client.create_aws_client()

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will try to download, decode and show the UserData contained in the enumerated EC2 instances.")

    print("[+] Module Functionality:\n")
    print("\tThe module will fetch the results of the 'ec2_enumerate_instances' module, and display")
    print("\tthe available EC2 instances to you. Then, you will choose from what instance you want to")
    print("\tretrieve the user data and the module will try to download it, decode it, and display it.\n")

    print("[+] IMPORTANT:\n")
    print("\tThis module depends on the 'ec2_enumerate_instances' module.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def fetch_enumeration_results(selected_session):
    try:
        enumeration_results_file = "./results/{}_session_data/ec2/ec2_enumerate_instances_results.json".format(selected_session)
        results_file = open(enumeration_results_file, 'r')
        results = json.load(results_file)

        return results

    except Exception:
        print(Fore.RED + "[-] No EC2 data found, please run the 'enumeration/ec2_enumerate_instances' module..." + Style.RESET_ALL)

def parse_enumeration_results(results):
    instance_ids = []

    for result_list in results['ec2']:
        for instance_list in result_list:
            for instance in instance_list:
                instance_ids.append(instance['InstanceId'])
    
    return instance_ids

def parse_options(instance_ids):
    if instance_ids:
            print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
            print("[+] Select Instances:\n")
            option = 1
            instance_options = {}
            for instance_id in instance_ids:
                instance_options[str(option)] = instance_id
                print("{} - {}".format(str(option), instance_id))
                option += 1
            selected_option = input("\nSelect Instance [Default=ALL]: ")
            if not selected_option:
                return instance_ids
            else:
                selected_instance = instance_options[str(selected_option)]
                return selected_instance

def download_user_data(botoconfig, session, instance_id, ec2_data):
    region = ""

    for result_list in ec2_data['ec2']:
        for instance_list in result_list:
            for instance in instance_list:
                if instance['InstanceId'] == instance_id:
                    region = instance['PrivateDnsName']
    
    region = region.split(".")
    instance_region = region[1]

    client = create_ec2_client(botoconfig, session, instance_region)

    response = client.describe_instance_attribute(
        Attribute='userData',
        DryRun=False,
        InstanceId=instance_id
    )

    return response

def parse_user_data(selected_session, user_data):
    print("\n[+] Available User Data:")

    available_data = []

    for data in user_data:
        instance_user_data = data['UserData']['Value']
        available_data.append(instance_user_data)
        print("\n[+] User data for " + Fore.GREEN + "{}".format(data['InstanceId']) + Style.RESET_ALL + " : {}".format(instance_user_data))

    results_path = './results/{}_session_data/ec2/ec2_download_user_data_results.json'.format(selected_session)
    print("\n[+] Done! Check " + Fore.GREEN + "{}".format(results_path) + Style.RESET_ALL + " for the results")

def main(botoconfig, session, selected_session):
    user_data = []

    available_ec2 = fetch_enumeration_results(selected_session)
    if not available_ec2:

        return None

    instance_ids = parse_enumeration_results(available_ec2)
    selected_option = parse_options(instance_ids)
    if isinstance(selected_option, list):
        for instance in selected_option:
            data = download_user_data(botoconfig, session, instance, available_ec2)
            if data['UserData']:
                user_data.append(data)
    else:
        data = download_user_data(botoconfig, session, selected_option, available_ec2)
        if data['UserData']:
            user_data.append(data)

    parse_user_data(selected_session, user_data)

    return user_data