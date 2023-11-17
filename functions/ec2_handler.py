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
    
    def describe_snapshots(self):
        snapshots = self.client.describe_snapshots()

        return snapshots

    def describe_account_attributes(self):
        attributes = self.client.describe_account_attributes()

        return attributes

    def describe_addresses(self):
        addresses = self.client.describe_addresses()

        return addresses

    def describe_availability_zones(self):
        zones = self.client.describe_availability_zones()

        return zones

    def describe_client_vpn_endpoints(self):
        endpoints = self.client.describe_client_vpn_endpoints()

        return endpoints 

    def describe_images(self):
        images = self.client.describe_images()

        return images 

    def describe_instance_status(self):
        status = self.client.describe_instance_status()

        return status 

    def describe_internet_gateways(self):
        gateways = self.client.describe_internet_gateways()

        return gateways

    def describe_key_pairs(self):
        keys = self.client.describe_key_pairs()

        return keys 

    def describe_launch_templates(self):
        templates = self.client.describe_launch_templates()

        return templates

    def describe_network_acls(self):
        acls = self.client.describe_network_acls()

        return acls

    def describe_security_groups(self):
        groups = self.client.describe_security_groups()

        return groups 

    def describe_subnets(self):
        subnets = self.client.describe_subnets()

        return subnets

    def describe_tags(self):
        tags = self.client.describe_tags()

        return tags

    def describe_volumes(self):
        volumes = self.client.describe_volumes()

        return volumes