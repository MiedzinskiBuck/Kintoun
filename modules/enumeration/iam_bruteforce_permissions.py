MODULE_METADATA = {
    "name": "iam_bruteforce_permissions",
    "display_name": "IAM Bruteforce Permissions",
    "category": "enumeration",
    "description": "Probe read-only AWS API actions to infer effective permissions when IAM policy introspection is unavailable.",
    "requires_region": False,
    "inputs": [
        {
            "name": "region",
            "type": "region",
            "required": False,
            "description": "Optional region. If empty, probe all configured regions for regional services.",
        }
    ],
    "output_type": "json",
    "risk_level": "medium",
    "execution_limits": {
        "timeout_seconds": 7200,
        "max_api_calls": 20000,
    },
}

import botocore
from functions import create_client, region_parser, utils


GLOBAL_SERVICES = [
    "iam",
    "sts",
    "s3",
    "cloudfront",
    "route53",
    "organizations",
]

REGIONAL_SERVICES = [
    "ec2",
    "lambda",
    "rds",
    "cloudformation",
    "cloudtrail",
    "logs",
    "events",
    "sns",
    "sqs",
    "kms",
    "ecr",
    "ecs",
    "eks",
    "secretsmanager",
    "dynamodb",
]

READ_ONLY_PREFIXES = ("List", "Get", "Describe")

DENIED_ERROR_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "UnauthorizedOperation",
    "UnauthorizedException",
    "UnrecognizedClientException",
}


def help():
    return


def collect_inputs():
    try:
        selected_region = input("Region (optional): ").strip()
    except RuntimeError:
        selected_region = ""
    return {"region": selected_region}


def eligible_operation_names(client):
    operations = []
    for op_name in client.meta.service_model.operation_names:
        if not op_name.startswith(READ_ONLY_PREFIXES):
            continue
        op_model = client.meta.service_model.operation_model(op_name)
        input_shape = op_model.input_shape
        required_members = set(getattr(input_shape, "required_members", []) or [])
        if required_members:
            continue
        operations.append(op_name)
    return operations


def classify_exception(exc):
    if isinstance(exc, botocore.exceptions.ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        if code in DENIED_ERROR_CODES or "AccessDenied" in code:
            return "denied", code, message
        return "unknown", code, message

    if isinstance(exc, botocore.exceptions.ParamValidationError):
        return "unknown", "ParamValidationError", str(exc)

    return "unknown", exc.__class__.__name__, str(exc)


def probe_service(client, service_name, region_label):
    allowed = []
    denied = []
    unknown = []

    for operation_name in eligible_operation_names(client):
        try:
            client._make_api_call(operation_name, {})
            allowed.append(operation_name)
        except Exception as exc:
            status, code, message = classify_exception(exc)
            item = {
                "operation": operation_name,
                "error_code": code,
                "message": message,
            }
            if status == "denied":
                denied.append(item)
            else:
                unknown.append(item)

    return {
        "service": service_name,
        "region": region_label,
        "allowed_actions": sorted(allowed),
        "denied_actions": denied,
        "unknown_actions": unknown,
        "counts": {
            "allowed": len(allowed),
            "denied": len(denied),
            "unknown": len(unknown),
            "total_tested": len(allowed) + len(denied) + len(unknown),
        },
    }


def build_client(botoconfig, session, service_name, region_name=None):
    try:
        return create_client.Client(botoconfig, session, service_name, region_name).create_aws_client()
    except Exception:
        return None


def main(botoconfig, session):
    inputs = collect_inputs()
    selected_region = inputs.get("region", "").strip()
    target_regions = [selected_region] if selected_region else region_parser.get_regions()

    probes = []
    service_errors = []

    for service_name in GLOBAL_SERVICES:
        client = build_client(botoconfig, session, service_name)
        if client is None:
            service_errors.append(
                {
                    "service": service_name,
                    "region": "global",
                    "error": "Could not create client.",
                }
            )
            continue
        probes.append(probe_service(client, service_name, "global"))

    for region in target_regions:
        for service_name in REGIONAL_SERVICES:
            client = build_client(botoconfig, session, service_name, region)
            if client is None:
                service_errors.append(
                    {
                        "service": service_name,
                        "region": region,
                        "error": "Could not create client.",
                    }
                )
                continue
            probes.append(probe_service(client, service_name, region))

    summary = {
        "total_service_probes": len(probes),
        "total_allowed": sum(p["counts"]["allowed"] for p in probes),
        "total_denied": sum(p["counts"]["denied"] for p in probes),
        "total_unknown": sum(p["counts"]["unknown"] for p in probes),
    }

    data = {
        "selected_region": selected_region or None,
        "regions_tested": target_regions if target_regions else [],
        "summary": summary,
        "service_errors": service_errors,
        "probes": probes,
    }
    return utils.module_result(data=data)
