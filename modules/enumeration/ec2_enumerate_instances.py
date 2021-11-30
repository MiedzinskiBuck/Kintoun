import boto3

def list_instances(session, region):
    try:
        print("[+] Enumerating Instances in {}".format(region))
        client = session.client('ec2', region_name=region)
        response = client.describe_instances()
        for instance in response['Reservations']:
            print("=====================================================================================")
            print("[+] Instance ID = {}".format(instance['Instances'][0]['InstanceId']))
            print("[+] Instance Status = {}".format(instance['Instances'][0]['State']['Name']))
            if instance['Instances'][0]['State']['Name'] == "running":
                print("[+] Public Address = {}".format(instance['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']))
            print(" ")
    except Exception as e:
        print(e)

def main(session):
    regions_file = open("data/regions.txt", "r")
    regions = regions_file.read().splitlines()
    print("[+] Available Regions...\n")
    for region in regions:
        print("- {}".format(region))
    selected_region = input("\n[+] Select region (Default All): ")
    if not selected_region:
        for region in regions:
            list_instances(session, region)
    elif selected_region not in regions:
        print("[-] Invalid Region...")
    else:
        list_instances(session, selected_region)
    
    