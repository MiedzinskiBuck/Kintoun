import os
import importlib
from functions import banner
from functions import help_functions

def list_available_modules():
    catalog = {}
    categories = os.listdir("./modules/")
    for category in categories:
        modules = os.listdir("./modules/{}/".format(category))
        catalog[category] = modules
    
    return catalog

def load_module(cmd, base_path):
     cmd_arguments = cmd.split()
     module_path = base_path + "/modules/{}".format(cmd_arguments[1])

     # module = importlib.import_module(module_path)
     module = __import__(module_path)

     print("Command: {}".format(cmd_arguments))
     print("Selected Module: {}".format(cmd_arguments[1]))
     print("Base Path: {}".format(base_path))
     print("Module Path: {}".format(module_path))
     # print("Imported Modules: {}".format(module))

def main():
    banner.Banner()

    available_commands = ['modules', 'exit', 'use', 'help']

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
                base_path = os.getcwd()
                load_module(cmd, base_path)
            elif check_cmd == "help":
                print("\n==============================\nAVAILABLE COMMANDS\n==============================")
                for command in available_commands:
                    print("- {}".format(command))
    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()