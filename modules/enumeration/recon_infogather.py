import json
from colorama import Fore, Style
from functions import utils, sts_handler, iam_handler, ec2_handler

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module provides a mechanism to attempt to validate the permissions assigned")
    print("\tto an AWS Account. This module will try to enumerate basic permissions by performing")
    print("\ta series of READ api calls. Since they are READ calls, this is a non-destructive module.")

    print("[+] Module Functionality:\n")
    print("\tJust run the module with the key/account you want to enumerate.")

def main(botoconfig, session):
    print("\n[+] Starting enumeration...")
    print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
    sts = sts_handler.STS(botoconfig, session)
    iam = iam_handler.IAM(botoconfig, session)

    print("[+] Getting account information...")
    account_info = sts.get_caller_identity() 
    print("Account Number: "+Fore.GREEN+"{}".format(account_info['Account'])+Style.RESET_ALL)
    print("User Arn: "+Fore.GREEN+"{}".format(account_info['Arn'])+Style.RESET_ALL)

    print("\n[+] Trying to enumerate permissions with IAM...")
    try:
        user_details, group_details, role_details, policy_details = iam.get_account_information()
        username = iam.whoami()
        policy_documents = utils.parse_account_information(username, user_details, group_details, role_details, policy_details)

        print("[+] Permission Set...")
        print(json.dumps(policy_documents, indent=4, default=str))
        print("[+] All information you need is here, there is no need to proceed...Exiting...")
        return
    except:
        print(f"\t{Fore.RED}- Unable to gather information, proceeding with brute force...{Style.RESET_ALL}")
        pass
    
    print("\n[+] Enumerating EC2 permissions...")
    regions_file = open("data/regions.txt", "r")
    regions = regions_file.read().splitlines()

    # Describe Instances
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_instances = ec2.describe_instances()
            if describe_instances:
                print(f"\t{Fore.GREEN}- ec2.describe_intances{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Snapshots 
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_snapshots = ec2.describe_snapshots()
            if describe_snapshots:
                print(f"\t{Fore.GREEN}- ec2.describe_snapshots{Style.RESET_ALL}")
                break
    except:
        pass

    # Describe Attributes 
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_attributes = ec2.describe_account_attributes()
            if describe_attributes:
                print(f"\t{Fore.GREEN}- ec2.describe_account_attributes{Style.RESET_ALL}")
                break
    except:
        pass

    # Describe Addresses
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_addresses = ec2.describe_addresses()
            if describe_addresses :
                print(f"\t{Fore.GREEN}- ec2.describe_addresses{Style.RESET_ALL}")
                break
    except:
        pass

    # Describe Availability Zones
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_zones = ec2.describe_availability_zones()
            if describe_zones:
                print(f"\t{Fore.GREEN}- ec2.describe_availability_zones{Style.RESET_ALL}")
                break
    except:
        pass

    # Describe VPN endpoints
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_vpn= ec2.describe_client_vpn_endpoints()
            if describe_vpn:
                print(f"\t{Fore.GREEN}- ec2.describe_client_vpn_endpoints{Style.RESET_ALL}")
                break
    except:
        pass

    # Describe Images
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_images = ec2.describe_images()
            if describe_images:
                print(f"\t{Fore.GREEN}- ec2.describe_images{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Instance Status
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_status = ec2.describe_instance_status()
            if describe_status :
                print(f"\t{Fore.GREEN}- ec2.describe_instance_status{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Internet Gateways
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_gateways = ec2.describe_internet_gateways()
            if describe_gateways:
                print(f"\t{Fore.GREEN}- ec2.describe_internet_gateways{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Key Pairs
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_keys = ec2.describe_key_pairs()
            if describe_keys:
                print(f"\t{Fore.GREEN}- ec2.describe_key_pairs{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Launch Templates
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_templates = ec2.describe_launch_templates()
            if describe_templates:
                print(f"\t{Fore.GREEN}- ec2.describe_launch_templates{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Network ACLS
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_acls = ec2.describe_network_acls()
            if describe_acls:
                print(f"\t{Fore.GREEN}- ec2.describe_network_acls{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Security Groups
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_groups = ec2.describe_security_groups()
            if describe_groups:
                print(f"\t{Fore.GREEN}- ec2.describe_security_groups{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Subnets
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_subnets = ec2.describe_subnets()
            if describe_subnets:
                print(f"\t{Fore.GREEN}- ec2.describe_subnets{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Tags 
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_tags = ec2.describe_tags()
            if describe_tags:
                print(f"\t{Fore.GREEN}- ec2.describe_tags{Style.RESET_ALL}")
                break
    except:
        pass
    
    # Describe Volumes
    try:
        for region in regions:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            describe_volumes = ec2.describe_volumes()
            if describe_volumes:
                print(f"\t{Fore.GREEN}- ec2.describe_volumes{Style.RESET_ALL}")
                break
    except:
        pass