import boto3

class Sts:

    def get_client(self, session):
        client = session.client('sts')
        return client

    def assume_role(self, client, acc_number, role_name, session_name):
        try:
            response = client.assume_role(
                    RoleArn='arn:aws:iam::{}:role/{}'.format(acc_number, role_name),
                    RoleSessionName=session_name,
                    DurationSeconds=3600
                    )
            return response
        except Exception as e:
            return(e.response["Error"]["Code"])
