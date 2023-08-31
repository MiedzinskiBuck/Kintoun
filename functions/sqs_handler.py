from functions import create_client

class SQS():

    """This class is responsible for handling all SQS api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "sqs", region).create_aws_client()

    def get_queue_url(self, queue_name, account_id):
        queue_url = self.client.get_queue_url(
            QueueName=queue_name,
            QueueOwnerAWSAccountId=account_id
        )

        return queue_url

    def read_messages(self, queue_url):
        response = self.client.receive_message(
            QueueUrl=str(queue_url),
            MaxNumberOfMessages=10,
            VisibilityTimeout=20,
            WaitTimeSeconds=20
        )

        print(response)