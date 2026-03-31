MODULE_METADATA = {
    "name": "iam_enumerate_role_trust_policy",
    "display_name": "IAM Enumerate Role Trust Policy",
    "category": "enumeration",
    "description": "Enumerate IAM role trust policies and list entities allowed to assume each role.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
    "result_view": "iam_enumerate_role_trust_policy",
    "dependencies": ["enumeration/iam_enumerate_roles"],
    "dependency_mode": "single",
    "dependency_payload_key": "roles",
}

import json
from functions import iam_handler, utils


ASSUME_ACTIONS = {
    "sts:AssumeRole",
    "sts:AssumeRoleWithSAML",
    "sts:AssumeRoleWithWebIdentity",
    "sts:TagSession",
    "sts:SetSourceIdentity",
}


def help():
    return


def _to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_role_names_from_dependency(context):
    if not isinstance(context, dict):
        return []
    dependency_context = context.get("dependency_context", {})
    by_module = dependency_context.get("by_module", {}) if isinstance(dependency_context, dict) else {}
    dependency_runs = by_module.get("enumeration/iam_enumerate_roles", [])
    if not dependency_runs:
        return []
    first_dep = dependency_runs[0] if isinstance(dependency_runs[0], dict) else {}
    dep_data = first_dep.get("data", {}) if isinstance(first_dep, dict) else {}
    role_items = dep_data.get("roles", []) if isinstance(dep_data, dict) else []
    role_names = []
    for role in role_items:
        if isinstance(role, dict) and role.get("role_name"):
            role_names.append(role["role_name"])
    return role_names


def _role_names_fallback(iam):
    role_names = []
    response = iam.enumerate_roles()
    if not response:
        return role_names

    for role in response.get("Roles", []):
        if role.get("RoleName"):
            role_names.append(role.get("RoleName"))

    while response.get("IsTruncated") and response.get("Marker"):
        response = iam.enumerate_roles(marker=response.get("Marker"))
        if not response:
            break
        for role in response.get("Roles", []):
            if role.get("RoleName"):
                role_names.append(role.get("RoleName"))
    return role_names


def _parse_policy_doc(policy_doc):
    if isinstance(policy_doc, dict):
        return policy_doc
    if isinstance(policy_doc, str):
        try:
            return json.loads(policy_doc)
        except Exception:
            return {}
    return {}


def _statement_allows_assume(statement):
    if not isinstance(statement, dict):
        return False
    if statement.get("Effect") != "Allow":
        return False
    actions = _to_list(statement.get("Action"))
    return any(action in ASSUME_ACTIONS for action in actions if isinstance(action, str))


def _extract_entities(statement):
    entities = []
    principal = statement.get("Principal")
    if principal == "*":
        return [{"principal_type": "Wildcard", "value": "*"}]
    if not isinstance(principal, dict):
        return entities

    for principal_type, values in principal.items():
        for value in _to_list(values):
            entities.append({"principal_type": principal_type, "value": value})
    return entities


def main(botoconfig, session, context=None):
    iam = iam_handler.IAM(botoconfig, session)
    role_names = _extract_role_names_from_dependency(context)
    dependency_used = True
    if not role_names:
        dependency_used = False
        role_names = _role_names_fallback(iam)

    role_results = []
    errors = []
    total_entities = 0

    for role_name in sorted(set(role_names)):
        role_resp = iam.get_role(role_name)
        if not role_resp:
            errors.append(f"Failed to retrieve role details for {role_name}")
            continue

        role = role_resp.get("Role", {})
        assume_doc = _parse_policy_doc(role.get("AssumeRolePolicyDocument"))
        statements = _to_list(assume_doc.get("Statement"))
        trusted_entities = []
        parsed_statements = []

        for statement in statements:
            if not _statement_allows_assume(statement):
                continue
            entities = _extract_entities(statement)
            trusted_entities.extend(entities)
            parsed_statements.append(
                {
                    "sid": statement.get("Sid"),
                    "effect": statement.get("Effect"),
                    "actions": _to_list(statement.get("Action")),
                    "entities": entities,
                    "condition": statement.get("Condition", {}),
                }
            )

        dedup = set()
        normalized_entities = []
        for entity in trusted_entities:
            key = (entity.get("principal_type"), entity.get("value"))
            if key in dedup:
                continue
            dedup.add(key)
            normalized_entities.append(entity)

        total_entities += len(normalized_entities)
        role_results.append(
            {
                "role_name": role.get("RoleName"),
                "role_arn": role.get("Arn"),
                "trusted_entity_count": len(normalized_entities),
                "trusted_entities": normalized_entities,
                "assume_role_statements": parsed_statements,
            }
        )

    data = {
        "dependency_used": dependency_used,
        "count_roles": len(role_results),
        "count_trusted_entities": total_entities,
        "roles": role_results,
    }
    return utils.module_result(data=data, errors=errors)
