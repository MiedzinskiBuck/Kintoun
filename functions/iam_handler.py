from functions import create_client

class IAM():

    """This class is responsible for handling all IAM api calls."""

    def __init__(self, botoconfig, session):
        self.client = create_client.Client(botoconfig, session, "iam").create_aws_client()

    def get_username(self):
        username = self.client.get_user()['User']['UserName']

        return username

    def whoami(self):
        username = self.client.get_user()['User']['UserName']

        return username

    def get_account_information(self):
        user_details = []
        group_details = []
        role_details = []
        policy_details = []

        response = self.client.get_account_authorization_details()

        if response.get('UserDetailList'):
            user_details.extend(response['UserDetailList'])
        if response.get('GroupDetailList'): 
            group_details.extend(response['GroupDetailList'])
        if response.get('RoleDetailList'):
            role_details.extend(response['RoleDetailList'])
        if response.get('Policies'):
            policy_details.extend(response['Policies'])

        while response['IsTruncated']:
            response = self.client.get_account_authorization_details(Marker=response['Marker'])

            if response.get('UserDetailList'):
                user_details.extend(response['UserDetailList'])
            if response.get('GroupDetalList'): 
                group_details.extend(response['GroupDetailList'])
            if response.get('RoleDetailList'):
                role_details.extend(response['RoleDetailList'])
            if response.get('Policies'):
                policy_details.extend(response['Policies'])

        return user_details, group_details, role_details, policy_details
    
    def parse_account_information(self, username, user_details, group_details, role_details, policy_details):
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
        pass

    def enumerate_users(self):
        users = self.client.list_users()

        return users
