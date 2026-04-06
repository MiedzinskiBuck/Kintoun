MODULE_METADATA = {
    "name": "iam_assume_role",
    "display_name": "IAM Assume Role",
    "category": "lateral_movement",
    "description": "Attempt to assume a target IAM role and hand off temporary credentials to the orchestrator.",
    "requires_region": False,
    "inputs": [
        {
            "name": "target_role",
            "type": "string",
            "required": True,
            "description": "Role ARN or role name from iam_enumerate_roles output.",
        },
        {
            "name": "external_id",
            "type": "string",
            "required": False,
            "description": "Optional ExternalId if required by trust policy.",
        },
        {
            "name": "session_name",
            "type": "string",
            "required": False,
            "description": "Optional role session name.",
        },
        {
            "name": "duration_seconds",
            "type": "integer",
            "required": False,
            "description": "Optional session duration in seconds (900-43200).",
        },
    ],
    "output_type": "json",
    "risk_level": "medium",
    "result_view": "default",
    "dependencies": ["enumeration/iam_enumerate_roles"],
    "dependency_mode": "single",
    "dependency_payload_key": "roles",
}

import datetime as dt
import botocore
from functions import iam_handler, utils


def help():
    return


def collect_inputs():
    try:
        target_role = input("Target role (ARN or name): ").strip()
    except RuntimeError:
        target_role = ""
    try:
        external_id = input("External ID (optional): ").strip()
    except RuntimeError:
        external_id = ""
    try:
        session_name = input("Session name (optional): ").strip()
    except RuntimeError:
        session_name = ""
    try:
        duration_raw = input("Duration seconds (optional): ").strip()
    except RuntimeError:
        duration_raw = ""
    return {
        "target_role": target_role,
        "external_id": external_id,
        "session_name": session_name,
        "duration_seconds": duration_raw,
    }


def _extract_role_map_from_dependency(context):
    role_map = {}
    if not isinstance(context, dict):
        return role_map
    dependency_context = context.get("dependency_context", {})
    if not isinstance(dependency_context, dict):
        return role_map
    by_module = dependency_context.get("by_module", {})
    if not isinstance(by_module, dict):
        return role_map

    dependency_runs = by_module.get("enumeration/iam_enumerate_roles", [])
    for dep in dependency_runs:
        if not isinstance(dep, dict):
            continue
        dep_data = dep.get("data", {})
        if not isinstance(dep_data, dict):
            continue
        for role in dep_data.get("roles", []):
            if not isinstance(role, dict):
                continue
            role_name = role.get("role_name")
            role_arn = role.get("arn")
            if role_name and role_arn:
                role_map[role_name] = role_arn
    return role_map


def _resolve_role_arn(target_role, role_map, iam):
    if target_role.startswith("arn:aws:iam::"):
        return target_role
    if target_role in role_map:
        return role_map[target_role]
    role_resp = iam.get_role(target_role)
    if role_resp and isinstance(role_resp, dict):
        role = role_resp.get("Role", {})
        if isinstance(role, dict) and role.get("Arn"):
            return role.get("Arn")
    return None


def _parse_duration_seconds(value):
    if not value:
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < 900:
        return 900
    if parsed > 43200:
        return 43200
    return parsed


def main(botoconfig, session, context=None):
    _ = botoconfig
    inputs = collect_inputs()
    target_role = (inputs.get("target_role") or "").strip()
    external_id = (inputs.get("external_id") or "").strip()
    session_name = (inputs.get("session_name") or "").strip()
    duration_seconds = _parse_duration_seconds(inputs.get("duration_seconds"))

    if not target_role:
        return utils.module_result(
            status="error",
            data={},
            errors=["Target role is required (ARN or role name)."],
        )

    iam = iam_handler.IAM(botoconfig, session)
    role_map = _extract_role_map_from_dependency(context)
    role_arn = _resolve_role_arn(target_role, role_map, iam)
    if not role_arn:
        return utils.module_result(
            status="error",
            data={"target_role": target_role},
            errors=["Unable to resolve target role ARN from dependency data or IAM GetRole."],
        )

    sts_client = session.client("sts", config=botoconfig)
    assume_params = {
        "RoleArn": role_arn,
        "RoleSessionName": session_name or f"kintoun-assume-{int(dt.datetime.now(dt.timezone.utc).timestamp())}",
    }
    if external_id:
        assume_params["ExternalId"] = external_id
    if duration_seconds:
        assume_params["DurationSeconds"] = duration_seconds

    try:
        response = sts_client.assume_role(**assume_params)
    except botocore.exceptions.ClientError as exc:
        return utils.module_result(
            status="error",
            data={"target_role": target_role, "role_arn": role_arn},
            errors=[str(exc)],
        )

    creds = response.get("Credentials", {})
    assumed_role_user = response.get("AssumedRoleUser", {})
    data = {
        "target_role": target_role,
        "role_arn": role_arn,
        "assumed_role_arn": assumed_role_user.get("Arn"),
        "assumed_role_id": assumed_role_user.get("AssumedRoleId"),
        "packed_policy_size": response.get("PackedPolicySize"),
        "assumed_credentials": {
            "access_key_id": creds.get("AccessKeyId"),
            "secret_access_key": creds.get("SecretAccessKey"),
            "session_token": creds.get("SessionToken"),
            "expiration": str(creds.get("Expiration")),
            "role_arn": role_arn,
        },
    }
    return utils.module_result(data=data)
