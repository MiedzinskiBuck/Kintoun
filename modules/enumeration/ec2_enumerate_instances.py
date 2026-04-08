MODULE_METADATA = {
    "name": "ec2_enumerate_instances",
    "display_name": "EC2 Enumerate All Instances",
    "category": "enumeration",
    "description": "Enumerate EC2 instances in a selected region or across all regions.",
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
    "result_view": "ec2_enumerate_instances",
}

import botocore
from functions import ec2_handler, region_parser, utils


def help():
    return


def collect_inputs():
    try:
        selected_region = input("Region (optional): ").strip()
    except RuntimeError:
        # No interactive input provided by runner: default to all regions.
        selected_region = ""
    return {"region": selected_region}


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


def main(botoconfig, session):
    inputs = collect_inputs()
    selected_region = inputs.get("region", "").strip()
    regions = [selected_region] if selected_region else region_parser.get_regions()
    results = {"regions": {}, "errors": []}
    total = 0

    for region in regions:
        try:
            ec2 = ec2_handler.EC2(botoconfig, session, region)
            response = ec2.describe_instances()
            if not response:
                results["regions"][region] = []
                continue

            region_instances = parse_instances(response)
            while response.get("NextToken"):
                response = ec2.describe_instances(response["NextToken"])
                if not response:
                    break
                region_instances.extend(parse_instances(response))

            results["regions"][region] = region_instances
            total += len(region_instances)
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as exc:
            results["regions"][region] = []
            results["errors"].append({"region": region, "error": str(exc)})

    results["total_instances"] = total
    return utils.module_result(data=results, errors=[])
