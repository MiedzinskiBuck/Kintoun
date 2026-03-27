import botocore
from functions import create_client


class Cloudformation():
    """This class is responsible for handling all CloudFormation api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "cloudformation", region).create_aws_client()

    def list_stacks(self, token=None):
        try:
            if token:
                return self.client.list_stacks(NextToken=token)
            return self.client.list_stacks()
        except botocore.exceptions.ClientError:
            return False

    def get_template(self, stack_id):
        try:
            return self.client.get_template(StackName=stack_id)
        except botocore.exceptions.ClientError:
            return False
