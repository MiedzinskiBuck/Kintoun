import boto3
import sys
import argparse

def main():
    banner.Banner()
    args = get_arguments()
    profile = args.profile
    try:
        session = get_session(profile)
    except Exception as e:
        print(e)
    if args.help:
        help_functions.Help()
        exit(0)

    # Console #######################################################################

    if args.console and not args.profile:
        print("[-] Please specify the profile to be used with -p")
        exit(0)
    if args.console and args.profile:
        create_console_link(session, profile)

    # IAM Functions #################################################################
    if args.iam_recon:
        iam_recon(session)
    if args.brute_role:
        if not args.wordlist or not args.acc_number:
            print("[-] Error: Missing parameters... [-]")
            print("==========================================================")
            print("Parameters required for BruteForcing AWS Roles:")
            print("Wordlist: '-w' or '--wordlist'")
            print("Account Number: '-a' or '--acc_number'")
            print("Session Name: '-n' or '--session_name'")
            exit(0)
        else:
            brute_role(session, args.wordlist, args.acc_number, args.session_name)

    # S3 Functions  #################################################################
    if args.s3_recon:
        bucket_recon(session)

    # EC2 Functions #################################################################
    if args.ec2_start_instances:
        ec2_start_instance(session)
    if args.ec2_stop_instances:
        ec2_stop_instance(session)
    if args.ec2_list_instances:
        ec2_list_all_instances(session)

    # STS Functions #################################################################
    if args.key_info:
        print("[+] Please type the access key to be used...")
        key = input("Access Key: ")
        sts_get_account_number(session, key)

if __name__ == "__main__":
    main()
