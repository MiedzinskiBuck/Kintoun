import boto3
import sys
import argparse
import iam_functions
import s3_functions

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--profile", dest="profile", nargs='?', const="default", help="Specify the AWS profile to use.")
    parser.add_argument("-i", "--iam_recon", dest="iam_recon", help="Perform basic recon routines on IAM permissions", action="store_true")
    parser.add_argument("-s", "--s3_recon", dest="s3_recon", help="Perform basic recon routines on s3 buckets", action="store_true")

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

def main():
    args = get_arguments()
    profile = args.profile
    try:
        session = get_session(profile)
    except Exception as e:
        print(e)
    if args.iam_recon:
        iam_recon(session)
    if args.s3_recon:
        bucket_recon(session)

if __name__ == "__main__":
    main()
