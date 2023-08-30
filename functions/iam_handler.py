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

    def enumerate_users(self):
        users = self.client.list_users()

        return users
