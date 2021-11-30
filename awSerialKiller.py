import boto3
import os
import importlib
from functions import banner
from functions import help_functions

def list_available_modules():
    catalog = {}
    categories = os.listdir("./modules/")
    for category in categories:
        try:
            modules = os.listdir("./modules/{}/".format(category))
            catalog[category] = modules
        except NotADirectoryError:
            pass
    
    return catalog

def load_module(cmd, session):
    cmd_arguments = cmd.split()

    try:
        module_path = "modules/{}".format(cmd_arguments[1])
        module_path = module_path.replace('/', '.').replace('\\', '.')

        module = importlib.import_module(module_path)
        module.main(session)
    except ModuleNotFoundError:
        print("\n[-] Module not found...\n[-] Type 'modules' for a list of available modules...")

def main():
    banner.Banner()
    available_commands = ['modules', 'exit', 'use', 'help']

    profile = input("[+] Profile to be used: ")

    if not profile:
        profile = "default"

    session = boto3.Session(profile_name=profile)

    print("[+] Using profile: {}\n".format(profile))
    print("[+] Ready to begin! Type 'modules' for a list of available modules.")

    try:
        while True:
            cmd = input("\n$ ")
            check_cmd = cmd.lower().split()[0]

            if check_cmd not in available_commands:
                print("\n[-] Unavailable module, type 'modules' for a list of available modules.")

            elif check_cmd == "modules":
                available_modules = list_available_modules()
                print("\n==============================\nAVAILABLE MODULES\n==============================")
                for module_category in available_modules:
                    print("\n{}\n".format(module_category.upper()))
                    for module in available_modules[module_category]:
                        print("- {}/{}".format(module_category, module.strip(".py")))
                        
            elif check_cmd == "exit":
                print("\nGoodbye!")
                break

            elif check_cmd == "use":
                load_module(cmd, session)

            elif check_cmd == "help":
                print("\n==============================\nAVAILABLE COMMANDS\n==============================")
                for command in available_commands:
                    print("- {}".format(command))

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()