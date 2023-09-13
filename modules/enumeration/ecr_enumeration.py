from colorama import Fore, Style
from functions import ecr_handler, sts_handler, utils

def help():
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Module Description:\n")
    print("\tThis module will enumerate ecr repositories and images on the account.")
    print("\tThe default options will enumerate ecr images in all regions.\n")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

def get_optional_regions():
    optional_region = utils.region_parser()

    return optional_region 

def main(botoconfig, session):
    print(Fore.YELLOW + "\n================================================================================================" + Style.RESET_ALL)
    print("[+] Starting ECR enumeration...")
    region_option = get_optional_regions()
    sts = sts_handler.STS(botoconfig, session)
    account_id = sts.get_caller_identity()['Account']

    for region in region_option:
        print(f"[+] Enumerating Images in {Fore.GREEN}{region}{Style.RESET_ALL}")
        ecr = ecr_handler.ECR(botoconfig, session, region)
        repositories = ecr.describe_repositories(account_id)
        repository_list = []
        if repositories:
            if repositories.get('repositories'):
                repository_list.extend(repositories['repositories'])

                while repositories.get('NextToken'):
                    repositories = ecr.describe_repositories(account_id, repositories['NextToken'])
                    if repositories.get('repositories'):
                        repository_list.extend(repositories['repositories'])
                        
            if repository_list:
                print(repository_list)
                
