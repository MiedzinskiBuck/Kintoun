import boto3
import botocore.exceptions
from colorama import Fore, Style
from functions import create_client
from functions import region_parser

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate ec2 instances on the account.")
    print("\tThe default options will enumerate ec2 instances in all regions.\n")

    print("\tThe module will print available ec2 instances, status and, if available, its public ip.")
    print("\tOn the stored results, it will store all available information about the ec2 instances,")
    print("\tgiving you a complete description of all information found.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def create_ec2_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, "ec2", region)
    return client.create_aws_client()

def get_optional_regions():
    optional_region = region_parser.Region()

    return optional_region 

def list_instances(botoconfig, session, region):
    try:
        print("[+] Enumerating Instances in {}".format(region))
        client = create_ec2_client(botoconfig, session, region)
        response = client.describe_instances(MaxResults=1000)
        instance_data = []
        for reservation in response['Reservations']:
            if reservation.get('Instances'):
                instance_data.extend(reservation['Instances'])

                while response.get('NextToken'):
                    response = client.describe_instances(MaxResults=1000, NextToken=response['NextToken'])
                    for reservation in response['Reservations']:
                        if reservation.get('Instances'):
                            instance_data.extend(reservation['Instances'])
                            
        return instance_data

    except botocore.exceptions.ClientError as e:
        print(Fore.RED + str(e) + Style.RESET_ALL)

def parse_instance_data(instance_data):
    try:
        for instance in instance_data:
            print(Fore.GREEN + "\n[+] Instance ID = {}".format(instance['InstanceId']) + Style.RESET_ALL)
            print(Fore.GREEN + "[+] Instance Status = {}".format(instance['State']['Name']) + Style.RESET_ALL)
            if instance['State']['Name'] == "running":
                print(Fore.GREEN + "[+] Public Address = {}".format(instance['NetworkInterfaces'][0]['Association']['PublicIp']) + Style.RESET_ALL)
            print("")
    except TypeError:
        pass

def main(botoconfig, session, selected_session):
    ec2_instances_data = []

    region_option = get_optional_regions()

    if region_option:
        for region in region_option:
            instance_data = list_instances(botoconfig, session, region)
            if instance_data:
                ec2_instances_data.append(instance_data)
                parse_instance_data(instance_data)

    return ec2_instances_data