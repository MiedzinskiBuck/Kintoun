import boto3

def iam_enumerate_users(session):
    client = session.client('iam')
    response = client.list_users()

    return response

def main(session):
    users = iam_enumerate_users(session)
    for user in users["Users"]:
        print("=========================================")
        print("[+] UserName: {}".format(user["UserName"]))
        print("[+] Arn: {}".format(user["Arn"]))

    return users