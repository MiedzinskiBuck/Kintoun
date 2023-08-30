import boto3
from colorama import Fore, Style
from modules.enumeration import iam_enumerate_permissions
from functions import iam_handler

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate the assume role policy for the existing roles.")
    print("\tIt will take advantage os the 'iam_enumerate_permissions' module.\n")

    print("\tTo function, the module will load the 'iam_enumerate_permissions.get_account_information'")
    print("\tand use the 'role_details' results to enumerate available roles.")
    print("\tWith the available roles, it will enumerate the 'AssumeRolePolicyDocument' and show")
    print("\twhich principal can enumerate which role...")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_assumable_roles(iam):
    user_details, group_details, role_details, policy_details = iam.get_account_information()
    username = iam.whoami()

    current_user = None
    
    for user in user_details:
        if user['UserName'] == username:
            print("[+] Found User: "+Fore.GREEN+"{}".format(user['UserName']+Style.RESET_ALL))
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

    return role_details

def parse_results(role_details):
    for role in role_details:
        if role['AssumeRolePolicyDocument']:
            print("\n[+] Role " + Fore.GREEN + "{}".format(role['Arn']) + Style.RESET_ALL + " can be assumed by:")
            for principal in role['AssumeRolePolicyDocument']['Statement']:
                print(Fore.YELLOW + "\t{}".format(principal['Principal']) + Style.RESET_ALL)
    
def main(botoconfig, session):
    print("\n[+] Starting enumeration of Assume Role Policies on the account...")
    iam = iam_handler.IAM(botoconfig, session)
    assumable_roles = get_assumable_roles(iam)

    print("[+] Parsing results...")

    parse_results(assumable_roles)

    role_results = {}

    for role in assumable_roles:
        if role['AssumeRolePolicyDocument']:
            for principal in role['AssumeRolePolicyDocument']['Statement']:
                role_results[role['Arn']] = principal['Principal']

    return role_results