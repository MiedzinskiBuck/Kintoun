import boto3

def iam_enumerate_users(session):
    client = session.client('iam')
    response = client.list_users()

    return response

def main(selected_session, session):
    users = iam_enumerate_users(session)
    for user in users["Users"]:
        print("\n[+] UserName: {}".format(user["UserName"]))
        print("[+] Arn: {}".format(user["Arn"]))

    return users