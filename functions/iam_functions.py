import boto3

class Iam:

    def get_client_name(self, session):
        client = session.client('iam')
        return client

    def get_client_username(self, client):
        username = client.get_user()["User"]["UserName"]
        return username

    def get_attached_policies(self, client, username):
        return client.list_attached_user_policies(UserName=username)["AttachedPolicies"]

    def get_attached_groups(self, client, username):
        return client.list_groups_for_user(UserName=username)
