import boto3
import json

def create_client(botoconfig, session):
    client = session.client('iam', config=botoconfig)

    return client

def get_username(client):
    username = client.get_user()['User']['UserName']

    return username

def get_account_information(client):

    user_details = []
    group_details = []
    role_details = []
    policy_details = []

    response = client.get_account_authorization_details()

    if response.get('UserDetailList'):
        user_details.extend(response['UserDetailList'])
    if response.get('GroupDetailList'): 
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

def main(botoconfig, session):
    print("\n[+] Starting Permissions Enumeration for current user....")

    client = create_client(botoconfig, session)
    user_details, group_details, role_details, policy_details = get_account_information(client)
    username = get_username(client)

    current_user = None
    
    for user in user_details:
        if user['UserName'] == username:
            print("[+] Found User: {}".format(user['UserName']))
            current_user = user
            break

    print("[+] Gathering inline policy documents....")

    policy_documents = []

    if current_user.get('UserPolicyList'):
        for inline_policy in current_user['UserPolicyList']:
            policy_documents.append(inline_policy['PolicyDocument'])

    print("[+] Gathering managed policy documents....")

    if current_user.get('AttachedManagedPolicies'):
        for managed_policy in current_user['AttachedManagedPolicies']:
            policy_arn = managed_policy['PolicyArn']
            for policy_detail in policy_details:
                if policy_detail['Arn'] == policy_arn:
                    default_version = policy_detail['DefaultVersionId']
                    for version in policy_detail['PolicyVersionList']:
                        if version['VersionId'] == default_version:
                            policy_documents.append(version['Document'])
                            break
                    break                        
    
    print("[+] Gathering group policy documents....")

    if current_user.get('GroupList'):
        for user_group in current_user['GroupList']:
            for group in group_details:
                if group['GroupName'] == user_group:
                    if group.get('GroupPolicyList'):
                        for inline_policy in group['GroupPolicyList']:
                            policy_documents.append(inline_policy['PolicyDocument'])
                        if group.get('AttachedManagedPolicies'):
                            for managed_policy in group['AttachedManagedPolicies']:
                                policy_arn = managed_policy['PolicyArn']
                                for policy in policy_details:
                                    if policy['Arn'] == policy_arn:
                                        default_version = policy['DefaultVersionId']
                                        for version in policy['PolicyVersionList']:
                                            if version['VersionId'] == default_version:
                                                policy_documents.append(version['Document'])
                                                break
                                        break

    print("\n[+] Permissions Set...")
    print(json.dumps(policy_documents, indent=4, default=str))

    return policy_documents