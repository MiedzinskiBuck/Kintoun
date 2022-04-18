from rx import create
import boto3
import requests
import urllib.parse
import json
from colorama import Fore, Style
from functions import create_client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will create a link to be pasted on your browser to start")
    print("\ta console session with the permissions of your selected profile.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
    
def get_console_link(session, botoconfig):

    client = create_client.Client(botoconfig, session, 'sts')
    sts = client.create_aws_client()

    res = sts.get_federation_token(
        Name='AWSFederateLogin',
        Policy=json.dumps({
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': '*',
                    'Resource': '*'
                }
            ]
        })
    )

    params = {
        'Action': 'getSigninToken',
        'Session': json.dumps({
            'sessionId': res['Credentials']['AccessKeyId'],
            'sessionKey': res['Credentials']['SecretAccessKey'],
            'sessionToken': res['Credentials']['SessionToken']
        })
    }

    federation_response = requests.get(url='https://signin.aws.amazon.com/federation', params=params)

    signin_token = federation_response.json()['SigninToken']

    params = {
        'Action': 'login',
        'Issuer': 'default' or '',
        'Destination': 'https://console.aws.amazon.com/console/home',
        'SigninToken': signin_token
    }

    url = 'https://signin.aws.amazon.com/federation?{}'.format(urllib.parse.urlencode(params))
    return(url)

def main(botoconfig, session, selected_session):
    
    print("\n[+] Getting login information...\n")
    try:
        console_link = get_console_link(session, botoconfig)
        print("[+] Console Link: {}".format(console_link))
    except Exception as e:
        print(e)