import boto3
import requests
import urllib.parse
import json

def get_console_link(session):

    sts = session.client('sts')

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

def main(selected_session, session):
    
    print("[+] Getting login information...\n")
    try:
        console_link = get_console_link(session)
        print("[+] Console Link: {}".format(console_link))
    except Exception as e:
        print(e)