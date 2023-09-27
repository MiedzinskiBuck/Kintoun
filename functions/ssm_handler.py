import botocore
import botocore.exceptions
from functions import create_client

class SSM():

    """This class is responsible for handling all SSM api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "ssm", region).create_aws_client()

    def get_caller_identity(self):
        response = self.client.get_caller_identity()

        return response

    def describe_instance_information(self, instance_id):
        try:
            response = self.client.describe_instance_information(Filters=[
                {
                    'Key': 'InstanceIds',
                    'Values': [
                        instance_id
                    ]
                }
            ])
        except:
            return None

        return response

    def send_command(self, instance_id, command):
        response = self.client.send_command(
            InstanceIds=[
                instance_id
            ],
            DocumentName='AWS-RunShellScript',
            Comment='TestComment',
            Parameters={
                'commands': [
                    command
                ]
            })

        return response

    def get_command_invocation(self, instance_id, command_id):
        response = self.client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )

        return response