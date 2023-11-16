import boto3
import botocore
from colorama import Fore, Style
from functions import create_client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will try to enumerate existing secrets, decrypt them and show the results.")
    print("\tSecrets Manager associates every secret with a KMS key, so this module will try to")
    print("\tenumerate those keys as well.")

    print("[+] Module Functionality:\n")
    print("\t")
    print("\t")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def create_secrets_manager_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, 'secretsmanager', region)

    return client.create_aws_client()

def list_target_secrets(botoconfig, session, region):
    print("[+] Searching for secrets on the "+ Fore.YELLOW+ "{}".format(region) + Style.RESET_ALL + " region...")
    secrets_list = {}
    secrets_list['SecretList'] = []
    try:
        client = create_secrets_manager_client(botoconfig, session, region)
        response = client.list_secrets()
        for secret in response['SecretList']:
            secrets_list['SecretList'].append(secret)

        try:
            while response['NextToken']:
                response = client.list_secrets(NextToken=response['NextToken'])
                for secret in response['SecretList']:
                    secrets_list['SecretList'].append(secret)
        except KeyError:
            pass

        return secrets_list
    except botocore.exceptions.ClientError as e:
        print(Fore.RED + "[-] Couldn't enumerate secrets for {}".format(region) + Style.RESET_ALL)

def get_secrets_value(client, secret_data):
    try:
        arn = secret_data['ARN']

        response = client.get_secret_value(
            SecretId=arn
        )

        return response
    except Exception as e:
        print(f"[-] Failte to retrieve secret: {e}")

def parse_secrets_value(botoconfig, secrets_data, session):
    secrets_data_list = []
    
    region_list = list(secrets_data)
    for region in region_list:
        if secrets_data[region]['SecretList']:
            print("\n[+] Secrets found on "+Fore.GREEN+"{}\n".format(region)+Style.RESET_ALL)
            client = create_secrets_manager_client(botoconfig, session, region)
            for secret in secrets_data[region]['SecretList']:
                secret_value = get_secrets_value(client, secret)
                secrets_data_list.append(secret_value)
                try:
                    print(f"\tSecret String:{Fore.GREEN}{secret_value['SecretString']}{Style.RESET_ALL}")
                    print(f"\tARN: {Fore.GREEN}{secret_value['ARN']}{Style.RESET_ALL}")
                except Exception:
                    pass

    return secrets_data_list

def main(botoconfig, session):
    print("\n[+] Starting Secrets Enumeration...")

    secrets_data_list = {}
    
    regions_file = open("data/regions.txt", "r")
    regions = regions_file.read().splitlines()
    print("\n[+] Available Regions...\n")
    for region in regions:
        print("- {}".format(region))
    selected_region = input("\n[+] Select region (Default All): ")
    if not selected_region:
        for region in regions:
            secrets_data = list_target_secrets(botoconfig, session, region)
            if secrets_data:
                secrets_data_list[region] = secrets_data
    elif selected_region not in regions:
        print("[-] Invalid Region...")
    else:
        secrets_data = list_target_secrets(botoconfig, session, selected_region)
        if secrets_data:
            secrets_data_list[selected_region] = secrets_data

    parsed_secrets = parse_secrets_value(botoconfig, secrets_data_list, session)

    return parsed_secrets
