from colorama import Fore, Style
from functions import ec2_handler, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate ec2 instances on the account.")
    print("\tThe default options will enumerate ec2 instances in all regions.\n")

    print("\tThe module will print available ec2 instances, status and, if available, its public ip.")
    print("\tOn the stored results, it will store all available information about the ec2 instances,")
    print("\tgiving you a complete description of all information found.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_optional_regions():
    optional_region = utils.region_parser()

    return optional_region 

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting EC2 enumeration...")
    region_option = get_optional_regions()

    for region in region_option:
        print(f"[+] Enumerating Instances in {Fore.GREEN}{region}{Style.RESET_ALL}")
        ec2 = ec2_handler.EC2(botoconfig, session, region)
        instances = ec2.describe_instances()
        instance_data = []
        if instances:
            for reservation in instances['Reservations']:
                if reservation.get('Instances'):
                    instance_data.extend(reservation['Instances'])

                    while instances.get('NextToken'):
                        instances = ec2.describe_instances(instances['NextToken'])
                        for reservation in instances['Reservations']:
                            if reservation.get('Instances'):
                                instance_data.extend(reservation['Instances'])
            
            if instance_data:
                for instance in instance_data:
                    print(f"=============================================\nInstanceId: {instance['InstanceId']}\nState: {instance['State']}\nAddress: {instance['PublicDnsName']}")