MODULE_METADATA = {
    "name": "lambda_enumerate_functions",
    "display_name": "Lambda Enumerate Functions",
    "category": "enumeration",
    "description": "Enumerate Lambda functions in a selected region or across all regions.",
    "requires_region": False,
    "inputs": [
        {
            "name": "region",
            "type": "region",
            "required": False,
            "description": "Optional AWS region. Leave empty to enumerate all regions.",
        }
    ],
    "output_type": "json",
    "risk_level": "low",
    "result_view": "lambda_enumerate_functions",
}

from functions import lambda_handler, region_parser, utils


def help():
    return


def collect_inputs():
    try:
        selected_region = input("Region (optional): ").strip()
    except RuntimeError:
        selected_region = ""
    return {"region": selected_region}


def parse_functions(resp):
    items = []
    for fn in resp.get("Functions", []):
        items.append(
            {
                "function_name": fn.get("FunctionName"),
                "function_arn": fn.get("FunctionArn"),
                "runtime": fn.get("Runtime"),
                "handler": fn.get("Handler"),
                "role": fn.get("Role"),
                "timeout": fn.get("Timeout"),
                "memory_size": fn.get("MemorySize"),
                "last_modified": fn.get("LastModified"),
                "code_size": fn.get("CodeSize"),
                "package_type": fn.get("PackageType"),
                "state": fn.get("State"),
            }
        )
    return items


def main(botoconfig, session):
    inputs = collect_inputs()
    selected_region = inputs.get("region", "").strip()
    regions = [selected_region] if selected_region else region_parser.get_regions()
    results = {"regions": {}, "errors": []}
    total = 0

    for region in regions:
        lamb = lambda_handler.Lambda(botoconfig, session, region)
        response = lamb.list_functions()
        if not response:
            results["regions"][region] = []
            results["errors"].append(
                {
                    "region": region,
                    "error": "Failed to list Lambda functions in this region.",
                }
            )
            continue

        region_functions = parse_functions(response)
        while response.get("NextMarker"):
            response = lamb.list_functions(response.get("NextMarker"))
            if not response:
                break
            region_functions.extend(parse_functions(response))

        results["regions"][region] = region_functions
        total += len(region_functions)

    results["total_functions"] = total
    return utils.module_result(data=results, errors=[])
