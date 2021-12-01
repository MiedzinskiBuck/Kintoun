import boto3

def list_instances(session, region):
    try:
        print("[+] Enumerating Instances in {}".format(region))
        client = session.client('ec2', region_name=region)
        response = client.describe_instances()
        instance_data = []
        for instance in response['Reservations']:
            instance_data.append(instance)
        return instance_data
    except Exception as e:
        print(e)

def parse_instance_data(instance_data):
    try:
        for instance in instance_data:
            print("=====================================================================================")
            print("[+] Instance ID = {}".format(instance['Instances'][0]['InstanceId']))
            print("[+] Instance Status = {}".format(instance['Instances'][0]['State']['Name']))
            if instance['Instances'][0]['State']['Name'] == "running":
                print("[+] Public Address = {}".format(instance['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']))
            print("")
    except TypeError:
        pass

def main(session):
    ec2_instances_data = []

    regions_file = open("data/regions.txt", "r")
    regions = regions_file.read().splitlines()
    print("[+] Available Regions...\n")
    for region in regions:
        print("- {}".format(region))
    selected_region = input("\n[+] Select region (Default All): ")
    if not selected_region:
        for region in regions:
            instance_data = list_instances(session, region)
            if instance_data:
                ec2_instances_data.append(instance_data)
                parse_instance_data(instance_data)
    elif selected_region not in regions:
        print("[-] Invalid Region...")
    else:
        instance_data = list_instances(session, selected_region)
        if instance_data:
            ec2_instances_data.append(instance_data)
            parse_instance_data(instance_data)
    
    regions_file.close()

    return ec2_instances_data