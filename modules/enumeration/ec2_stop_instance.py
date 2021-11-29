import boto3

def ec2_stop_instance(session):
    instance_id = input("Instance ID: ")
    region = input("Region: ")
    try:
        print("[-] Stopping instance {}".format(instance_id))
        client = session.client('ec2', region_name=region)
        ec2 = ec2_functions.Ec2()
        ec2.stop_selected_instance(session, instance_id)
        print("[-] Instance Stopped!")
    except Exception as e:
        print(e)
