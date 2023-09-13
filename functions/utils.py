def parse_account_information(username, user_details, group_details, role_details, policy_details):
    current_user = None
    
    for user in user_details:
        if user['UserName'] == username:
            current_user = user
            break

    policy_documents = []

    if current_user.get('UserPolicyList'):
        for inline_policy in current_user['UserPolicyList']:
            policy_documents.append(inline_policy['PolicyDocument'])

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

    return policy_documents

def region_parser():
    regions_file = open("data/regions.txt", "r")
    regions = regions_file.read().splitlines()
    print("[+] Available Regions...\n")

    for region in regions:
        print("- {}".format(region))
    selected_region = input("\n[+] Select region (Default All): ")

    if not selected_region:
        selected_regions = []
        for region in regions:
            selected_regions.append(region)
        return selected_regions

    elif selected_region not in regions:
        print("[-] Invalid Region...")
        return False

    else:
        selected_region = [selected_region]
        return selected_region