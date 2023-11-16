import boto3
import botocore

class Client():

    """This Class is designed to create the necessary client to interact with AWS services.
    It will create attributes based on the parameters passed to it and create a client that can be used to interact with the services."""

    def __init__(self, botoconfig, session, service, region=None):
        self.botoconfig = botoconfig
        self.session = session
        self.service = service
        if region != None:
            self.region = region

    def create_aws_client(self):
        try:
            client = self.session.client(self.service, config=self.botoconfig, region_name=self.region)
            return client
        except:
            client = self.session.client(self.service, config=self.botoconfig)
            return client
