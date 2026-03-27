import botocore
from functions import create_client


class S3():
    """This class is responsible for handling all S3 api calls."""

    def __init__(self, botoconfig, session):
        self.client = create_client.Client(botoconfig, session, "s3").create_aws_client()

    def list_buckets(self):
        try:
            return self.client.list_buckets()
        except botocore.exceptions.ClientError:
            return False

    def list_objects(self, bucket, token=None):
        try:
            if token:
                return self.client.list_objects_v2(Bucket=bucket, MaxKeys=1000, ContinuationToken=token)
            return self.client.list_objects_v2(Bucket=bucket, MaxKeys=1000)
        except botocore.exceptions.ClientError:
            return False
