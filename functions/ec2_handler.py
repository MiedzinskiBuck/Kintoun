import botocore
from functions import create_client

class EC2():

    """This class is responsible for handling all EC2 api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "ec2", region).create_aws_client()
    
    def describe_instances(self, token=None):
        try:
            if token:
                instances = self.client.describe_instances(MaxResults=1000, NextToken=token)
            else:
                instances = self.client.describe_instances(MaxResults=1000)
        except botocore.exceptions.ClientError as e:
            return False

        return instances

    def describe_attributes(self, attribute, instanceId):
        attribute = self.client.describe_instance_attribute(
            Attribute=attribute,
            InstanceId=instanceId
        )

        return attribute