MODULE_METADATA = {
    "name": "ec2_enumerate_instances",
    "display_name": "EC2 Enumerate Instances",
    "category": "enumeration",
    "description": "Enumerate EC2 instances across all configured regions.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

import botocore
from functions import ec2_handler, region_parser, utils


def help():
    return


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
    regions = region_parser.get_regions()
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
        except botocore.exceptions.ClientError as exc:
            results["regions"][region] = []
            results["errors"].append({"region": region, "error": str(exc)})

    results["total_instances"] = total
    return utils.module_result(data=results, errors=[])
