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
    "result_view": "default",
    "execution_limits": {
        "timeout_seconds": 900,
        "max_api_calls": 3000,
    },
    "dependencies": [],
    "dependency_mode": "single",
    "dependency_payload_key": None,
}

from functions import utils


def help():
    return


def collect_inputs():
    # input_value = input("Example input: ")
    # return {"example_input": input_value}
    return {}


def main(botoconfig, session, context=None):
    _ = (botoconfig, session)
    _ = context
    inputs = collect_inputs()
    result_data = {
        "message": "Template module executed.",
        "inputs": inputs,
    }
    return utils.module_result(data=result_data)
