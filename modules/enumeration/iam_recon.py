import boto3

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
