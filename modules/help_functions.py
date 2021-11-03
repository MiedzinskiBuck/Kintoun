import sys

class Help:

    def __init__(self):
        print("\nUsage: {} [MODULE] [FLAGS]\n".format(sys.argv[0]))
        print("================================================================================================")
        print("Flags Available: ")
        print("================================================================================================")
        print("\n\t-p, --profile = Select the profile to use [Default profile = default]. ")
        print("\n==============================================================================================")
        print("Available Modules...")
        print("================================================================================================")
        print("\n\t[+] IAM Modules\n")
        print("\t-i, --iam_recon = Start IAM recon.")
        print("\n")
        print("\n\t-b, --brute_role = Start brute force of roles to be impersonated.")
        print("\t\t-w, --wordlist = Roles wordlist.")
        print("\t\t-a, --acc_number = Select the account number to try to bruteforce.")
        print("\t\t-n, --session_name = Select the session name to use upon successfull impersonation.")
        print("\n\t[+] S3 Modules\n")
        print("\t-s, --s4_recon = Start S3 recon.")
        print("\t\t-h, --help = Print this help and exit.")
        print("\n\t[+] EC2 Modules\n")
        print("\t-el, --ec2_list_instances = Lists all available EC2 instances.")
        print("\t-est, --ec2_start_instances = Start the selected EC2 instance.")
        print("\t-esp, --ec2_stop_instances = Stop the selected EC2 instance.")

