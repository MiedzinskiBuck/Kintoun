import tempfile
import time
from functions import region_parser as _region_parser
from functions.no_color import Fore, Style


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
    return _region_parser.select_regions()


def module_result(data=None, status="ok", errors=None):
    if errors is None:
        errors = []
    return {
        "status": status,
        "data": data,
        "errors": errors
    }


def create_temp_zip_path():
    temp_file = tempfile.NamedTemporaryFile(prefix="kintoun_lambda_", suffix=".zip", delete=False)
    temp_file.close()
    return temp_file.name


def poll_until(check_fn, interval_seconds=10, max_attempts=36):
    for _ in range(max_attempts):
        if check_fn():
            return True
        time.sleep(interval_seconds)
    return False


def print_section(message):
    print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)
    print(message)
    print(Fore.YELLOW + "===================================================================================================================" + Style.RESET_ALL)


def error_result(message):
    return module_result(status="error", errors=[message])
