import boto3
import json

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

def store_results(selected_session, user_details, group_details, role_details, policy_details):
    print('[+] Storing results...')

    user_file = open("results/{}_session_data/iam/user_data.json".format(selected_session), "w")
    json.dump(user_details, user_file, default=str)
    user_file.close()

    group_file = open("results/{}_session_data/iam/group_data.json".format(selected_session), "w")
    json.dump(user_details, group_file, default=str)
    group_file.close()

    role_file = open("results/{}_session_data/iam/role_data.json".format(selected_session), "w")
    json.dump(user_details, role_file, default=str)
    role_file.close()

    policy_file = open("results/{}_session_data/iam/policy_data.json".format(selected_session), "w")
    json.dump(user_details, policy_file, default=str)
    policy_file.close()

def main(selected_session, session):
    user_details, group_details, role_details, policy_details = get_account_information(session)
    store_results(selected_session, user_details, group_details, role_details, policy_details)