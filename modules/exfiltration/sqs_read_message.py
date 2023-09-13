import signal
import time
import readchar
from colorama import Fore, Style
from functions import sqs_handler

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will create a loop that will attempt to read messages from a specified SQS queue")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def handler(signum, frame):
    msg = "[-] Ctrl + C pressed. Exit? y/n"
    print(msg, end="", flush=True)
    res = readchar.readchar()

    if res == 'y':
        print("")
        exit(1)
    else:
        print("", end="\r", flush=True)
        print(" " * len(msg), end="", flush=True)
        print("      ", end="\r", flush=True)

def main(botoconfig, session):
    sqs = sqs_handler.SQS(botoconfig, session, "sa-east-1")
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting SQS exfiltration module...")
    q_url = input("[+] Insert queue URL: ") 

    print("[+] Retrieving Messages...")
    read = True

    signal.signal(signal.SIGINT, handler)

    while read:
        message = sqs.read_messages(q_url)
        print("\n")
        print(message)
        #time.sleep(2)