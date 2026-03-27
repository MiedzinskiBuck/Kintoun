import botocore
from functions import create_client


class Lambda():
    """This class is responsible for handling all Lambda api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "lambda", region).create_aws_client()

    def list_functions(self, marker=None):
        try:
            if marker:
                return self.client.list_functions(Marker=marker)
            return self.client.list_functions()
        except botocore.exceptions.ClientError:
            return False
