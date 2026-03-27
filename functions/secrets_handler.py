import botocore
from functions import create_client


class Secrets():
    """This class is responsible for handling all Secrets Manager api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "secretsmanager", region).create_aws_client()

    def list_secrets(self, token=None):
        try:
            if token:
                return self.client.list_secrets(NextToken=token)
            return self.client.list_secrets()
        except botocore.exceptions.ClientError:
            return False

    def get_secret_value(self, secret_arn):
        try:
            return self.client.get_secret_value(SecretId=secret_arn)
        except botocore.exceptions.ClientError:
            return False
