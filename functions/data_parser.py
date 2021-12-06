import json
import sys
from pathlib import Path

class Parser:

    def session_select(self):
        check_file = Path("data/session_data.json")
        if check_file.is_file():
            data_file = json.load(open("data/session_data.json"))
            print("================================================================================================")
            print("[+] Select Session:\n")
            print("0 - New Session")
            option = 1
            for session_data in data_file:
                session = list(session_data.keys())[0]
                print("{} - {}".format(str(option), session))
                option += 1
            selected_option = input("\nSession: ")
            if not selected_option:
                print("\n[-] No session selected....exiting...")
                sys.exit()
            selected_option = int(selected_option)
            if selected_option == 0:
                selected_session = input("[+] Please name your session: ")
                json_data = {selected_session : []}
                data_file.append(json_data)
                write_file = open("data/session_data.json", "w")
                json.dump(data_file, write_file, default=str)
                write_file.close()
            else:
                selected_option -= 1
                selected_session = list(data_file[selected_option].keys())[0]
        else:
            data_file = open("data/session_data.json", "w")
            print("================================================================================================")
            selected_session = input("[+] Please name your session: ")
            json_data = '[{"' + selected_session + '" : []}]'
            data_file.write(json_data)
            
        return selected_session
    
    def parse_module_results(self, executed_command, module_results):
        executed_module = executed_command.split("/")[1]
        data_category = executed_module.split("_")[0]

        parsed_data = {}
        parsed_data[data_category] = module_results

        return parsed_data 

    def store_parsed_results(self, selected_session, parsed_results):
        data_file = open('data/session_data.json', 'r')
        json_data = json.load(data_file)
        data_file.close()
        for session in json_data:
            try:
                session[selected_session].append(parsed_results)
            except:
                pass

        data_file = open('data/session_data.json', 'w')
        json.dump(json_data, data_file, default=str)