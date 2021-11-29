import boto3

def sts_get_account_number(session, key):
    print("\n[+] Fetching account number...")
    sts = sts_functions.Sts()
    client = sts.get_client(session)
    account_number = sts.get_account_number(client, key)
    print("[+] Account Number: {}".format(account_number))
