from colorama import Fore, Style
from functions import ec2_handler, utils

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

def get_optional_regions():
    optional_region = utils.region_parser()

    return optional_region 

def get_user_data(ec2, instance_data):
    user_data = {}
    for instance in instance_data:
        data = ec2.describe_attributes('userData', instance['InstanceId'])
        user_data[instance['InstanceId']] = data['UserData']['Value']
    
    return user_data

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting EC2 user data download...")
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
                print("[+] Instances Found! Retrieving user data...")
                user_data = get_user_data(ec2, instance_data)
                print(user_data)
