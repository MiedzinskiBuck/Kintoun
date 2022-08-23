import boto3
import botocore

class Credential:
    
    def __init__(self, credentials):
        self.profile = credentials["profile"]
        self.aws_access_key_id = credentials["aws_access_key_id"]
        self.aws_secret_access_key = credentials["aws_secret_access_key"]
        self.aws_session_token = credentials["aws_session_token"]
        self.session = self.getSession()
        
    def getSession(self):
        return boto3.Session(
            profile_name=self.profile,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token
        )