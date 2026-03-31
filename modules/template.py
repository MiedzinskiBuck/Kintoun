MODULE_METADATA = {
    "name": "my_module_name",
    "display_name": "My Module Name",
    "category": "enumeration",
    "description": "Describe what this module does in one clear sentence.",
    "requires_region": False,
    "inputs": [
        {
            "name": "example_input",
            "type": "string",
            "required": False,
            "description": "Describe this input and expected format.",
        }
    ],
    "output_type": "json",
    "risk_level": "low",
}

from functions import utils


def help():
    return


def collect_inputs():
    # input_value = input("Example input: ")
    # return {"example_input": input_value}
    return {}


def main(botoconfig, session):
    _ = (botoconfig, session)
    inputs = collect_inputs()
    result_data = {
        "message": "Template module executed.",
        "inputs": inputs,
    }
    return utils.module_result(data=result_data)
