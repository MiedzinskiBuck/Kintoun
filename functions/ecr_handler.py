import botocore
from functions import create_client

class ECR():

    """This class is responsible for handling all ECR api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "ecr", region).create_aws_client()

    def describe_repositories(self, accountId, token=None):
        try:
            if token:
                response = self.client.describe_repositories(
                    registryId=accountId,
                    nextToken=token,
                    maxResults=1000
                )
            else:
                response = self.client.describe_repositories(
                    registryId=accountId,
                    maxResults=1000
                )
        except botocore.exceptions.ClientError as e:
            return False
        
        return response
