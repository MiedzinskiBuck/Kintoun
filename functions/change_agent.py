import random
import boto3
import botocore
from colorama import Fore, Style

class Agent:
    def get_agent_config(self):
        user_agents_file = open("data/user_agents.txt", "r")
        safe_user_agents = user_agents_file.read().splitlines()

        user_agent = boto3.session.Session()._session.user_agent().lower()

        if 'kali'in user_agent.lower() or 'parrot' in user_agent.lower() or 'pentoo' in user_agent.lower():
            print(Fore.RED + "[-] Running on pentesting system... Changing username..." + Style.RESET_ALL)
            user_agent = random.choice(safe_user_agents)
            print(Fore.GREEN + "[+] New user agent: " + Style.RESET_ALL + "{}".format(user_agent))
            botocore_config = botocore.config.Config(user_agent=user_agent)

            return botocore_config

        else:
            botocore_config = botocore.config.Config(user_agent=user_agent)

            return botocore_config