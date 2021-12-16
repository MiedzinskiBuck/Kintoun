import boto3
import json

# Understand if the user wants to enumerate permissions to all users or just one user

def get_all_users(session):
    print("Get all users")

def get_user(session, user):
    print("\n[+] Enumerating permissions for: {}".format(user))
    print("================================================================================================")
    client = session.client('iam')
    inline_policies = client.list_user_policies(UserName=user)
    managed_policies = client.list_attached_user_policies(UserName=user)
    print("[+] Inline Policies: ")
    for policy in inline_policies['PolicyNames']:
        print(policy)
    print("\n[+] Managed Policies: ")
    for policy in managed_policies['AttachedPolicies']:
        policyName = policy['PolicyName']
        policyArn = policy['PolicyArn']
        print("------------------------------------------------------------------------------------------------")
        print("Policy Name : {}".format(policyName))
        print("Policy Arn  : {}".format(policyArn))
        policy_details = client.get_policy(PolicyArn=policyArn)
        policyVersion = policy_details['Policy']['DefaultVersionId']
        policyPermissions = client.get_policy_version(PolicyArn=policyArn, VersionId=policyVersion)
        for policyStatement in policyPermissions['PolicyVersion']['Document']['Statement']:
            print(policyStatement['Action'])

def main(selected_session, session):
    users = json.load(open("./results/{}_session_data.json".format(selected_session), "r"))
    try:
        print("================================================================================================")
        print("[+] Select User:")
        option = 1
        available_users = {}
        for user in users['iam']['Users']:
            available_users[str(option)] = user["UserName"]
            print("{} - {}".format(str(option), user["UserName"]))
            option += 1
        selected_user = input("\n[+] User(Default = All): ")
        if not selected_user:
            get_all_users(session)
        else:
            get_user(session, available_users[selected_user])
    except Exception:
        print("[-] No users found...please run the 'enumeration/iam_enumerate_users' module first...")
        return None
    

