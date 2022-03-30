import boto3

def lambda_handler(event, context):
    client = boto3.client('iam')
    response = client.attach_user_policy(UserName = 'USERNAME', PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')

    return response

