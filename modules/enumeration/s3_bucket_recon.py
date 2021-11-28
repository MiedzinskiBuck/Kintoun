import boto3

def bucket_recon(session):
    s3 = s3_functions.Bucket()
    client = s3.get_client(session)
    allBuckets = s3.list_buckets(client)["Buckets"]
    for bucketName in allBuckets:
        print("[+] Bucket Name: {}".format(bucketName["Name"]))
        if s3.get_public_buckets(client, bucketName["Name"]):
            bucketPermission = "Public"
        else:
            bucketPermission = "NotPublic"
        print("[+] Permissions: {}".format(bucketPermission))
