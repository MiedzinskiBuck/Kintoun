import botocore
from functions import create_client


class RDS():
    """This class is responsible for handling all RDS api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "rds", region).create_aws_client()

    def describe_db_instances(self, marker=None):
        try:
            if marker:
                return self.client.describe_db_instances(Marker=marker)
            return self.client.describe_db_instances()
        except botocore.exceptions.ClientError:
            return False
