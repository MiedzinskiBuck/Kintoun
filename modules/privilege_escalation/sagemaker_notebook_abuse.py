import boto3
from colorama import Fore, Style

def create_client(botoconfig, session):
    client = session.client('SERVICE-CHANGE-THIS', config=botoconfig)
    return client

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\t")

    print("[+] Module Functionality:\n")
    print("\t")

    print("[+] IMPORTANT:\n")
    print("\t")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def check_permissions():
    # We need to check if we have the required permissions to escalate privileges with this technique.
    # The required  permissions are "sagemaker:CreateNotebookInstance", "sagemaker:CreatePresignedNotebookInstanceUrl" and "sagemaker:ListNotebookInstances"
    pass

def check_existing_notebooks():
    # We need to check the existing notebooks to evaluate if there is any that we could exploit.
    pass

def create_notebook():
    # We create a notebook and pass the selected role to it
    pass

def create_presigned_url():
    # We create a presigned url to access the notebook from the browser. Maybe this will be deprecated if I can automate this process without the browser.
    pass

def get_jupyter_credentials():
    # We use the notebooks terminal to get temporary credentials
    pass

def main(botoconfig, session, selected_session):
    pass