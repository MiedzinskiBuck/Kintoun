import boto3
import botocore

class Credential:
    
    def __init__(self, credential):
        self.credential = credential
        self.session = None
        self.startSession()

    def startSession(self):
        if not self.credential:
            self.credential = "Environment Variables"

        print(self.credential)