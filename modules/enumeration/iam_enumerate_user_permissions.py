import boto3
import os
import json

def iam_enumerate_users(session):
    client = session.client('iam')
    response = client.list_users()

    return response

def get_account_information(session):
    print('[+] Starting general account enumeration...')

    user_details = []
    group_details = []
    role_details = []
    policy_details = []

    client = session.client('iam')
    response = client.get_account_authorization_details()

    if response.get('UserDetailList'):
        user_details.extend(response['UserDetailList'])
    if response.get('GroupDetalList'): 
        group_details.extend(response['GroupDetailList'])
    if response.get('RoleDetailList'):
        role_details.extend(response['RoleDetailList'])
    if response.get('Policies'):
        policy_details.extend(response['Policies'])

    while response['IsTruncated']:
        response = client.get_account_authorization_details(Marker=response['Marker'])

        if response.get('UserDetailList'):
            user_details.extend(response['UserDetailList'])
        if response.get('GroupDetalList'): 
            group_details.extend(response['GroupDetailList'])
        if response.get('RoleDetailList'):
            role_details.extend(response['RoleDetailList'])
        if response.get('Policies'):
            policy_details.extend(response['Policies'])

    return user_details, group_details, role_details, policy_details

def get_all_users(session):
    print("\n================================================================================================")
    print("[+] Enumerating permissions for all users")
    print("================================================================================================")

def get_user(session, user):
    print("\n================================================================================================")
    print("[+] Enumerating permissions for: {}".format(user))
    print("================================================================================================")
    #client = session.client('iam')
    #inline_policies = client.list_user_policies(UserName=user)
    #managed_policies = client.list_attached_user_policies(UserName=user)
    #print("[+] Inline Policies: ")
    #for policy in inline_policies['PolicyNames']:
    #    print(policy)
    #print("\n[+] Managed Policies: ")
    #for policy in managed_policies['AttachedPolicies']:
    #    policyName = policy['PolicyName']
    #    policyArn = policy['PolicyArn']
    #    print("------------------------------------------------------------------------------------------------")
    #    print("Policy Name : {}".format(policyName))
    #    print("Policy Arn  : {}".format(policyArn))
    #    policy_details = client.get_policy(PolicyArn=policyArn)
    #    policyVersion = policy_details['Policy']['DefaultVersionId']
    #    policyPermissions = client.get_policy_version(PolicyArn=policyArn, VersionId=policyVersion)
    #    for policyStatement in policyPermissions['PolicyVersion']['Document']['Statement']:
    #        print(policyStatement['Action'])

def main(selected_session, session):
    print("[+] Starting Module...")
    file_path = "./results/{}_session_data.json".format(selected_session)

    users = iam_enumerate_users(session)

    # Need to read the user from the iam user enumeration results

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

    #user_details, group_details, role_details, policy_details = get_account_information(session)