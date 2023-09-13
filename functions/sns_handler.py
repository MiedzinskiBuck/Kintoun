from functions import create_client

class SNS():

    """This class is responsible for handling all SNS api calls."""

    def __init__(self, botoconfig, session, region):
        self.client = create_client.Client(botoconfig, session, "sns", region).create_aws_client()
    
    def list_topics(self):
        topics = self.client.list_topics()

        return topics

    def list_subscriptions(self):
        subscriptions = self.client.list_subscriptions()

        return subscriptions

    def subscribe_topic(self):
        response = self.client.subscribe(
            TopicArn='string',
            Protocol='string',
            Endpoint='string',
            Attributes={
                'string': 'string'
            },
            ReturnSubscriptionArn=True|False
        )

    def publish_topic(self):
        response = self.client.publish(
            TopicArn='string',
            TargetArn='string',
            PhoneNumber='string',
            Message='string',
            Subject='string',
            MessageStructure='string',
            MessageAttributes={
                'string': {
                    'DataType': 'string',
                    'StringValue': 'string',
                    'BinaryValue': b'bytes'
                    }
                },
            MessageDeduplicationId='string',
            MessageGroupId='string'
        )

        return response