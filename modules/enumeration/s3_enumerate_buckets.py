import boto3
from colorama import Fore, Back, Style

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate the S3 buckets available in the account.")
    print("\tIt will print the found buckets and give you the option to enumerate.")
    print("\tthe objects on those buckets.\n")

    print("\tIf you choose to enumerate objects on the found buckets, it will")
    print("\tprint the list of objects from each bucket.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def create_client(botoconfig, session):
    client = session.client('s3', config=botoconfig)

    return client

def list_buckets(client):
    response = client.list_buckets()

    return response

def parse_bucket_data(bucket_data):
    bucket_names = []
    for bucket in bucket_data['Buckets']:
        bucket_names.append(bucket['Name'])
    
    return bucket_names

def list_bucket_objects(client, bucket_names):

    bucket_objects = {}

    for bucket in bucket_names:
        response = client.list_objects_v2(Bucket=bucket, MaxKeys=1000)
        if response.get('Contents'):
            bucket_objects[bucket] = response['Contents']
        else:
            bucket_objects[bucket] = []
            continue

        while response['IsTruncated']:
            reponse = client.list_objects_v2(Bucket=bucket, MaxKeys=1000, ContinuationToken=response['NextContinuationToken'])
            bucket_objects[bucket].extend(response['Contains'])
    
    return bucket_objects

def main(botoconfig, session, selected_session):
    client = create_client(botoconfig, session)

    print("\n[+] Starting Bucket Enumeration...\n")
    bucket_data = list_buckets(client)
    bucket_names = parse_bucket_data(bucket_data)

    for bucket in bucket_names:
        print(Fore.GREEN + "[+] Bucket Name: " + Style.RESET_ALL + "{}".format(bucket))

    print("\n[-] Do you want to enumerate objects in those buckets?")
    enumerate_objects = input("[-] WARNING: This could generate a lot of traffic [N/y]: ")

    if enumerate_objects.lower() == "y" or enumerate_objects.lower() == "yes":
        print("\n[+] Starting Bucket Objects Enumeration...")
        bucket_objects = list_bucket_objects(client, bucket_names)

        for bucket in bucket_names:
            print(Fore.GREEN + "\n[+] Objects in bucket: " + Style.RESET_ALL + "{}\n".format(bucket))
            for object in bucket_objects.get(bucket):
                print("- {}".format(object.get('Key')))

    return bucket_data