import os
import importlib
from colorama import Fore, Style

class Modules:

    def list_available_modules(self):
        catalog = {}
        categories = os.listdir("./modules/")
        for category in categories:
            try:
                modules = os.listdir("./modules/{}/".format(category))
                catalog[category] = modules
            except NotADirectoryError:
                pass

        for module_category in catalog:
            if module_category.upper() == "__PYCACHE__" or module_category.upper() == "__INIT__":
                pass
            else:
                print(Fore.GREEN + "\n{}\n".format(module_category.upper()) + Style.RESET_ALL)
                for module in catalog[module_category]:
                    if module.upper() == "__PYCACHE__" or module.strip(".py").upper() == "__INIT__":
                        pass
                    else:
                        print("- {}/{}".format(module_category, module.strip(".py")))
    
    def module_help(self, cmd):
        cmd_arguments = cmd.split()

        try:
            module_path = "modules/{}".format(cmd_arguments[0])
            module_path = module_path.replace('/', '.').replace('\\', '.')

            module = importlib.import_module(module_path)
            module_info = module.help()

        except ModuleNotFoundError:
            raise ModuleNotFoundError("\n[-] Module not found...Type 'modules' for a list of available modules...")