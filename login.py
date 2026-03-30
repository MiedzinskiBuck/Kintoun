import json
import urllib.parse
import webbrowser
import requests
import boto3

# Assume role (ou usa profile atual)
sts = boto3.client("sts")

response = sts.get_caller_identity()
print(f"[+] Identity: {response['Arn']}")

# Se quiser assumir role, use assume_role aqui

creds = boto3.Session().get_credentials().get_frozen_credentials()

session = {
    "sessionId": creds.access_key,
    "sessionKey": creds.secret_key,
    "sessionToken": creds.token
}

session_json = json.dumps(session)

# Get signin token
url = "https://signin.aws.amazon.com/federation"
params = {
    "Action": "getSigninToken",
    "Session": session_json
}

r = requests.get(url, params=params)
signin_token = r.json()["SigninToken"]

# Generate login URL
login_url = (
    "https://signin.aws.amazon.com/federation?"
    + urllib.parse.urlencode({
        "Action": "login",
        "Issuer": "Script",
        "Destination": "https://console.aws.amazon.com/",
        "SigninToken": signin_token
    })
)

print(f"[+] Login URL:\n{login_url}")

# Abre automaticamente
webbrowser.open(login_url)
