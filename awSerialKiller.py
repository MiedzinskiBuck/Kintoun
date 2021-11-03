import boto3
import sys
import argparse
import banner
import help_functions
import iam_functions
import s3_functions
import sts_functions
import ec2_functions

def get_arguments():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-p", "--profile", dest="profile", nargs='?', const="default", help=argparse.SUPPRESS)
    parser.add_argument("-w", "--wordlist", dest="wordlist", help=argparse.SUPPRESS)
    parser.add_argument("-a", "--acc_number", dest="acc_number", help=argparse.SUPPRESS)
    parser.add_argument("-n", "--session_name", dest="session_name", help=argparse.SUPPRESS)
    parser.add_argument("-i", "--iam_recon", dest="iam_recon", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-s", "--s3_recon", dest="s3_recon", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-b", "--brute_role", dest="brute_role", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-el", "--ec2_list_instances", dest="ec2_list_instances", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-est", "--ec2_start_instances", dest="ec2_start_instances", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-esp", "--ec2_stop_instances", dest="ec2_stop_instances", help=argparse.SUPPRESS, action="store_true")
    parser.add_argument("-h", "--help", dest="help", help=argparse.SUPPRESS, action="store_true")

    args = parser.parse_args()

    return args

def get_session(profile):
    return boto3.Session(profile_name=profile)

def iam_recon(session):
    iam = iam_functions.Iam()
    client = iam.get_client_name(session)
    username = iam.get_client_username(client)
    allUserPolicies = iam.get_attached_policies(client, username)
    allUserGroups = iam.get_attached_groups(client, username)
    print("[+] Username: {}".format(username))
    for userPolicy in allUserPolicies:
        policyName = userPolicy["PolicyName"]
        print("[+] Attached User Policy: {}".format(policyName))
    for group in allUserGroups["Groups"]:
        groupName = group["GroupName"]
        print("[+] Attached Groups: {}".format(groupName))

def bucket_recon(session):
    s3 = s3_functions.Bucket()
    client = s3.get_client(session)
    allBuckets = s3.list_buckets(client)["Buckets"]
    for bucketName in allBuckets:
        print("[+] Bucket Name: {}".format(bucketName["Name"]))
        if s3.get_public_buckets(client, bucketName["Name"]):
            bucketPermission = "Public"
        else:
            bucketPermission = "NotPublic"
        print("[+] Permissions: {}".format(bucketPermission))

def brute_role(session, wordlist, acc_number, session_name):
    sts = sts_functions.Sts()
    client = sts.get_client(session)
    role_names_file = open(wordlist, 'r')
    role_names = role_names_file.readlines()
    for role_name in role_names:
        arn = "[+] Trying to impersonate role = arn:aws:iam::{}:role/{}".format(acc_number, role_name)
        print(arn, end='')
        AssumeRole = sts.assume_role(client, acc_number, role_name.strip(), session_name)
        if AssumeRole == "AccessDenied":
            pass
        elif AssumeRole["ResponseMetadata"]["HTTPStatusCode"] == 200:
            print("\n[+] Role Impersonation Successful [+]")
            print("==============================================")
            print("export AWS_ACCESS_KEY_ID={}".format(AssumeRole["Credentials"]["AccessKeyId"]))
            print("export AWS_SECRET_ACCESS_KEY={}".format(AssumeRole["Credentials"]["SecretAccessKey"]))
            print("export AWS_SESSION_TOKEN={}".format(AssumeRole["Credentials"]["SessionToken"]))
            break

def ec2_start_instance(session):
    instance_id = input("Instance ID: ")
    region = input("Region: ")
    try:
        print("[+] Starting instance {}".format(instance_id))
        client = session.client('ec2', region_name=region)
        ec2 = ec2_functions.Ec2()
        ec2.start_selected_instance(session, instance_id)
        print("[+] Instance Started!")
    except Exception as e:
        print(e)

def ec2_stop_instance(session):
    instance_id = input("Instance ID: ")
    region = input("Region: ")
    try:
        print("[-] Stopping instance {}".format(instance_id))
        client = session.client('ec2', region_name=region)
        ec2 = ec2_functions.Ec2()
        ec2.stop_selected_instance(session, instance_id)
        print("[-] Instance Stopped!")
    except Exception as e:
        print(e)

def ec2_list_all_instances(session):
    ec2 = ec2_functions.Ec2()
    regions_file = open('data/regions.txt', 'r')
    regions = regions_file.readlines()
    for region in regions:
        region = region.strip()
        try:
            print("\n[+] Listing EC2 instances on {}".format(region))
            ec2.list_instances(session, region)
        except Exception as e:
            print(e)

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

if __name__ == "__main__":
    main()
