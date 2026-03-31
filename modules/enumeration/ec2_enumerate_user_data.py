MODULE_METADATA = {
    "name": "ec2_enumerate_user_data",
    "display_name": "EC2 Enumerate User Data",
    "category": "enumeration",
    "description": "Enumerate EC2 instances and fetch User Data for each instance in a selected region or across all regions.",
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
    "risk_level": "medium",
    "result_view": "ec2_enumerate_user_data",
    "dependencies": ["enumeration/ec2_enumerate_instances"],
    "dependency_mode": "single",
    "dependency_payload_key": "regions",
}

import base64
import json
import botocore
from functions import ec2_handler, region_parser, utils


def help():
    return


def collect_inputs():
    try:
        selected_region = input("Region (optional): ").strip()
    except RuntimeError:
        selected_region = ""
    try:
        dependency_regions_json = input("Dependency regions JSON (optional): ").strip()
    except RuntimeError:
        dependency_regions_json = ""
    return {
        "region": selected_region,
        "dependency_regions_json": dependency_regions_json,
    }


def parse_instances(resp):
    items = []
    for reservation in resp.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            items.append(
                {
                    "instance_id": instance.get("InstanceId"),
                    "instance_type": instance.get("InstanceType"),
                    "state": instance.get("State", {}).get("Name"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "launch_time": str(instance.get("LaunchTime")),
                }
            )
    return items


def decode_user_data(value_b64):
    if not value_b64:
        return None
    try:
        return base64.b64decode(value_b64).decode("utf-8", errors="replace")
    except Exception:
        return None


def main(botoconfig, session, context=None):
    inputs = collect_inputs()
    selected_region = inputs.get("region", "").strip()
    dependency_regions_json = inputs.get("dependency_regions_json", "").strip()
    dependency_regions = {}
    has_dependency_regions = False

    # Preferred path: consume dependency context provided by the web runner.
    dependency_context = (context or {}).get("dependency_context", {}) if isinstance(context, dict) else {}
    by_module = dependency_context.get("by_module", {}) if isinstance(dependency_context, dict) else {}
    ec2_dependency_runs = by_module.get("enumeration/ec2_enumerate_instances", [])
    if ec2_dependency_runs:
        first_dep = ec2_dependency_runs[0]
        dep_data = first_dep.get("data", {}) if isinstance(first_dep, dict) else {}
        dep_regions = dep_data.get("regions", {}) if isinstance(dep_data, dict) else {}
        if isinstance(dep_regions, dict):
            dependency_regions = dep_regions
            has_dependency_regions = True

    # Backward-compatible fallback path: parse dependency regions passed as input JSON.
    if dependency_regions_json and not has_dependency_regions:
        try:
            parsed_dependency = json.loads(dependency_regions_json)
            if isinstance(parsed_dependency, dict):
                dependency_regions = parsed_dependency
                has_dependency_regions = True
        except Exception:
            dependency_regions = {}

    regions = [selected_region] if selected_region else region_parser.get_regions()

    results = {"regions": {}, "errors": []}
    total_instances = 0
    total_with_user_data = 0

    for region in regions:
        try:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            region_instances = dependency_regions.get(region, [])
            if not has_dependency_regions:
                response = ec2.describe_instances()
                if not response:
                    results["regions"][region] = {
                        "count_instances": 0,
                        "count_with_user_data": 0,
                        "instances": [],
                        "errors": ["Failed to enumerate instances in this region."],
                    }
                    continue

                region_instances = parse_instances(response)
                while response.get("NextToken"):
                    response = ec2.describe_instances(response.get("NextToken"))
                    if not response:
                        break
                    region_instances.extend(parse_instances(response))

            enriched_instances = []
            region_errors = []
            region_with_user_data = 0

            for instance in region_instances:
                instance_id = instance.get("instance_id")
                try:
                    attr = ec2.describe_attributes("userData", instance_id)
                    user_data_b64 = attr.get("UserData", {}).get("Value")
                    user_data_text = decode_user_data(user_data_b64)
                    has_user_data = user_data_b64 is not None
                    if has_user_data:
                        region_with_user_data += 1

                    enriched_instances.append(
                        {
                            **instance,
                            "has_user_data": has_user_data,
                            "user_data_base64": user_data_b64,
                            "user_data": user_data_text,
                        }
                    )
                except botocore.exceptions.ClientError as exc:
                    region_errors.append(
                        f"Failed to fetch user data for {instance_id}: {str(exc)}"
                    )
                    enriched_instances.append(
                        {
                            **instance,
                            "has_user_data": False,
                            "user_data_base64": None,
                            "user_data": None,
                        }
                    )

            total_instances += len(region_instances)
            total_with_user_data += region_with_user_data
            results["regions"][region] = {
                "count_instances": len(region_instances),
                "count_with_user_data": region_with_user_data,
                "instances": enriched_instances,
                "errors": region_errors,
            }
        except botocore.exceptions.ClientError as exc:
            results["regions"][region] = {
                "count_instances": 0,
                "count_with_user_data": 0,
                "instances": [],
                "errors": [str(exc)],
            }
            results["errors"].append({"region": region, "error": str(exc)})

    results["total_instances"] = total_instances
    results["total_with_user_data"] = total_with_user_data
    return utils.module_result(data=results, errors=[])
