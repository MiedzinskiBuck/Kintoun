import boto3

def generate_client(session):
    client = session.client('s3')

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

def main(selected_session, session):
    client = generate_client(session)

    print("\n[+] Starting Bucket Enumeration...")
    print("================================================================================================")
    bucket_data = list_buckets(client)
    bucket_names = parse_bucket_data(bucket_data)

    for bucket in bucket_names:
        print("[+] Bucket Name: {}".format(bucket))

    print("\n================================================================================================")
    print("[-] Do you want to enumerate objects in those buckets?")
    enumerate_objects = input("[-] WARNING: This could generate a lot of traffic [N/y]: ")

    if enumerate_objects.lower() == "y" or enumerate_objects.lower() == "yes":
        print("\n[+] Starting Bucket Objects Enumeration...")
        print("================================================================================================")
        bucket_objects = list_bucket_objects(client, bucket_names)

        for bucket in bucket_names:
            print("\n[+] Objects in bucket: {}".format(bucket))
            print("================================================================================================")
            for object in bucket_objects.get(bucket):
                print("- {}".format(object.get('Key')))

    return bucket_data