import boto3

def ec2_list_all_instances(session):
    ec2 = ec2_functions.Ec2()
    regions_file = open('data/regions.txt', 'r')
    regions = regions_file.readlines()
    for region in regions:
    region = region.strip()
    try:
    print("\n[+] Listing EC2 instances on {}".format(region))
    ec2.list_instances(session, region)
    except Exception as e:
    print(e)
