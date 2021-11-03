import boto3

class Ec2:

    def list_instances(self, session, region):
        session = boto3.Session()
        client = session.client('ec2', region_name=region)
        response = client.describe_instances()
        for instance in response['Reservations']:
            print("\n=====================================================================================")
            print("[+] Instance ID = {}".format(instance['Instances'][0]['InstanceId']))
            print("[+] Instance Status = {}".format(instance['Instances'][0]['State']['Name']))
            if instance['Instances'][0]['State']['Name'] == "running":
                print("[+] Public Address = {}".format(instance['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']))

    def stop_selected_instance(self, session, instance_id):
        session = boto3.Session()
        client = session.client('ec2', region_name='sa-east-1')
        client.stop_instances(InstanceIds=[instance_id])

    def start_selected_instance(self, session, instance_id):
        session = boto3.Session()
        client = session.client('ec2', region_name='sa-east-1')
        client.start_instances(InstanceIds=[instance_id])

