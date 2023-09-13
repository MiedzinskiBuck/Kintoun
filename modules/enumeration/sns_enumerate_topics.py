import signal
import time
import readchar
from colorama import Fore, Style
from functions import sns_handler, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will create a loop that will attempt to read messages from a specified SQS queue")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_optional_regions():
    optional_region = utils.region_parser()

    return optional_region 

def main(botoconfig, session):
    region_option = get_optional_regions()
    sns = sns_handler.SNS(botoconfig, session, "sa-east-1")

    if region_option:
        for region in region_option:
            pass
            # Do Stuff
