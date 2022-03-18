import boto3
import os
import re
import sys
import readline
from functions import banner
from functions import data_parser
from functions import module_handler
from functions import command_handler
from functions import change_agent
from colorama import Fore, Style
from botocore.exceptions import ProfileNotFound
        
def main():
    available_commands = ['modules', 'exit', 'use', 'help', 'run', 'results']

    banner.Banner()
    module_action = module_handler.Modules()
    command_action = command_handler.Commands()
    parser = data_parser.Parser()
    configuration = change_agent.Agent()

    RE_SPACE = re.compile('.*\s+$', re.M)
    catalog = parser.completion_data()

    class Completer(object):

        def _listdir(self, root):
            res = []
            for name in os.listdir(root):
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    name += os.sep
                res.append(name)

            return res

        def _complete_path(self, path=None):
            if not path:
                return self._listdir('.')
            dirname, rest = os.path.split(path)
            tmp = dirname if dirname else '.'
            res = [os.path.join(dirname, p) for p in self._listdir(tmp) if p.startswith(rest)]

            if len(res) > 1 or not os.path.exists(path):
                return res

            if os.path.isdir(path):
                return [os.path.join(path, p) for p in self._listdir(path)]
            return [path + ' ']

        def complete_extra(self, args):
            if not args:
                return self._complete_path('.')
            return self._complete_paths(args[-1])

        def complete(self, text, state):
            buffer = readline.get_line_buffer()
            line = readline.get_line_buffer().split()

            if not line:
                return [c + ' ' for c in catalog][state]
            
            if RE_SPACE.match(buffer):
                line.append('')
            cmd = line[0].strip()
            if cmd in catalog:
                impl = getattr(self, 'complete_%s' % cmd)
                args = line[1:]
                if args:
                    return (impl(args) + [None])[state]
                return [cmd + ' '][state]
            
            results = [c + ' ' for c in catalog if c.startswith(cmd)] + [None]

            return results[state]
    
    comp = Completer()

    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(comp.complete)

    botoconfig = configuration.get_agent_config()
    selected_session = parser.session_select()

    profile = input("\n[+] Profile to be used: ")

    if not profile:
        profile = "default"

    try:
        session = boto3.Session(profile_name=profile)
    except ProfileNotFound:
        print("[-] Profile not found... exiting...")
        sys.exit()

    print("\n[+] Using profile: " + Fore.GREEN + "{}\n".format(profile) + Style.RESET_ALL)
    print("[+] Ready to begin! Type 'modules' for a list of available modules.")
    print(Fore.YELLOW + "================================================================================================" + Style.RESET_ALL)

    try:
        while True:
            try:
                cmd = input("\nAWSerialKiller = [{}:{}] $ ".format(selected_session, profile))
                check_cmd = cmd.lower().split()

                if check_cmd[0] == "modules":
                    module_action.list_available_modules()
                            
                elif check_cmd[0] == "exit":
                    print("\nGoodbye!")
                    break

                elif check_cmd[1] == "use" or check_cmd[1] == "run":
                    module_results = module_action.load_module(cmd, botoconfig, session, selected_session)
                    if module_results == None:
                        pass
                    else:
                        try:
                            executed_module = cmd.lower().split()[0]
                            parsed_module_results = parser.parse_module_results(executed_module, module_results)
                            parser.store_parsed_results(selected_session, executed_module, parsed_module_results)
                        except Exception as e:
                            print("[-] Failed to store results: {}".format(e))

                elif check_cmd == "results":
                    parser.fetch_results(selected_session)

                elif check_cmd[1] == "help":
                    module_action.module_help(cmd)

                else:
                    print("\n[-] Unavailable command.")

            except Exception as e:
                print(e)

    except (KeyboardInterrupt):
            print("\n\nGoodbye!")

if __name__ == "__main__":
    main()