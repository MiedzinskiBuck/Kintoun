import boto3

class Bucket:

    def get_client(self, session):
        return session.client('s3')

    def list_buckets(self, client):
        return client.list_buckets()

    def get_public_buckets(self, client, bucket_name):
        return client.get_bucket_policy_status(Bucket=bucket_name)['PolicyStatus']['IsPublic']
