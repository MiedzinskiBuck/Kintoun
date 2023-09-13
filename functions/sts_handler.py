import botocore
from functions import create_client

class STS():

    """This class is responsible for handling all STS api calls."""

    def __init__(self, botoconfig, session):
        self.client = create_client.Client(botoconfig, session, "sts").create_aws_client()

    def get_caller_identity(self):
        response = self.client.get_caller_identity()

        return response