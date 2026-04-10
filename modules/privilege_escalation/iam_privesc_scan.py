MODULE_METADATA = {
    "name": "iam_privesc_scan",
    "display_name": "IAM PrivEsc Scan",
    "category": "privilege_escalation",
    "description": "Scan IAM roles for privilege-escalation risk by correlating powerful role permissions with cross-account assume-role trust.",
    "requires_region": False,
    "inputs": [
        {
            "name": "target_account_id",
            "type": "string",
            "required": False,
            "description": "Optional AWS account ID filter. If set, only cross-account trust to this account is considered.",
        }
    ],
    "output_type": "json",
    "risk_level": "high",
    "result_view": "iam_privesc_scan",
    "execution_limits": {
        "timeout_seconds": 1800,
        "max_api_calls": 20000,
    },
    "dependencies": [
        "enumeration/iam_enumerate_roles",
        "enumeration/iam_enumerate_role_trust_policy",
    ],
    "dependency_mode": "multiple",
}

import botocore
from functions import utils


HIGH_RISK_MANAGED_POLICIES = {
    "AdministratorAccess",
    "IAMFullAccess",
    "PowerUserAccess",
    "SecurityAudit",
}


def help():
    return


def collect_inputs():
    try:
        target_account_id = input("Target account ID filter (optional): ").strip()
    except RuntimeError:
        target_account_id = ""
    return {"target_account_id": target_account_id}


def _to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_current_identity(session, botoconfig):
    sts = session.client("sts", config=botoconfig)
    caller = sts.get_caller_identity()
    arn = caller.get("Arn", "")
    account_id = caller.get("Account", "")
    return account_id, arn


def _extract_roles_from_dependencies(context):
    if not isinstance(context, dict):
        return {}
    dependency_context = context.get("dependency_context", {})
    if not isinstance(dependency_context, dict):
        return {}
    by_module = dependency_context.get("by_module", {})
    if not isinstance(by_module, dict):
        return {}
    role_runs = by_module.get("enumeration/iam_enumerate_roles", [])
    role_map = {}
    for run in role_runs:
        if not isinstance(run, dict):
            continue
        data = run.get("data", {})
        if not isinstance(data, dict):
            continue
        for role in data.get("roles", []):
            if not isinstance(role, dict):
                continue
            role_name = role.get("role_name")
            if role_name:
                role_map[role_name] = role
    return role_map


def _extract_trust_from_dependencies(context):
    if not isinstance(context, dict):
        return {}
    dependency_context = context.get("dependency_context", {})
    if not isinstance(dependency_context, dict):
        return {}
    by_module = dependency_context.get("by_module", {})
    if not isinstance(by_module, dict):
        return {}
    trust_runs = by_module.get("enumeration/iam_enumerate_role_trust_policy", [])
    trust_map = {}
    for run in trust_runs:
        if not isinstance(run, dict):
            continue
        data = run.get("data", {})
        if not isinstance(data, dict):
            continue
        for role in data.get("roles", []):
            if not isinstance(role, dict):
                continue
            role_name = role.get("role_name")
            if role_name:
                trust_map[role_name] = role
    return trust_map


def _fallback_list_roles(iam):
    role_map = {}
    marker = None
    while True:
        if marker:
            response = iam.list_roles(Marker=marker)
        else:
            response = iam.list_roles()
        for role in response.get("Roles", []):
            role_name = role.get("RoleName")
            if role_name:
                role_map[role_name] = {
                    "role_name": role_name,
                    "arn": role.get("Arn"),
                    "path": role.get("Path"),
                    "description": role.get("Description"),
                }
        if not response.get("IsTruncated") or not response.get("Marker"):
            break
        marker = response.get("Marker")
    return role_map


def _parse_aws_account_from_principal(value):
    if not isinstance(value, str):
        return None
    if value == "*":
        return "*"
    if value.startswith("arn:aws:iam::"):
        parts = value.split(":")
        if len(parts) > 4:
            return parts[4]
    if value.isdigit() and len(value) == 12:
        return value
    return None


def _resolve_role_trust_entities(iam, role_name, dep_trust):
    if dep_trust and isinstance(dep_trust, dict):
        entities = dep_trust.get("trusted_entities", [])
        if isinstance(entities, list):
            return entities
    role_resp = iam.get_role(RoleName=role_name)
    role_data = role_resp.get("Role", {}) if isinstance(role_resp, dict) else {}
    assume_doc = role_data.get("AssumeRolePolicyDocument", {}) if isinstance(role_data, dict) else {}
    statements = _to_list(assume_doc.get("Statement")) if isinstance(assume_doc, dict) else []
    entities = []
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        if statement.get("Effect") != "Allow":
            continue
        actions = [a for a in _to_list(statement.get("Action")) if isinstance(a, str)]
        if not any(a.startswith("sts:AssumeRole") or a == "sts:*" for a in actions):
            continue
        principal = statement.get("Principal")
        if principal == "*":
            entities.append({"principal_type": "Wildcard", "value": "*"})
            continue
        if not isinstance(principal, dict):
            continue
        for p_type, p_values in principal.items():
            for p_val in _to_list(p_values):
                entities.append({"principal_type": p_type, "value": p_val})
    return entities


def _policy_document_is_powerful(policy_doc):
    if not isinstance(policy_doc, dict):
        return False, []
    reasons = []
    statements = _to_list(policy_doc.get("Statement"))
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        if statement.get("Effect") != "Allow":
            continue
        actions = [a for a in _to_list(statement.get("Action")) if isinstance(a, str)]
        resources = [r for r in _to_list(statement.get("Resource")) if isinstance(r, str)]
        has_star_action = "*" in actions or any(a.lower() == "iam:*" for a in actions)
        has_star_resource = "*" in resources
        if has_star_action and has_star_resource:
            reasons.append("Policy allows * on *")
        if any(a.lower() == "iam:passrole" for a in actions) and has_star_resource:
            reasons.append("Policy allows iam:PassRole on *")
        if any(a.lower().startswith("iam:createpolicyversion") for a in actions):
            reasons.append("Policy allows iam:CreatePolicyVersion")
        if any(a.lower().startswith("iam:attach") for a in actions):
            reasons.append("Policy allows IAM attach actions")
        if any(a.lower().startswith("sts:assumerole") for a in actions) and has_star_resource:
            reasons.append("Policy allows sts:AssumeRole on *")
    return len(reasons) > 0, sorted(set(reasons))


def _scan_role_policies(iam, role_name, policy_doc_cache=None):
    if policy_doc_cache is None:
        policy_doc_cache = {}
    attached_policy_names = []
    policy_reasons = []
    powerful = False

    marker = None
    while True:
        if marker:
            attached = iam.list_attached_role_policies(RoleName=role_name, Marker=marker)
        else:
            attached = iam.list_attached_role_policies(RoleName=role_name)
        for pol in attached.get("AttachedPolicies", []):
            policy_name = pol.get("PolicyName")
            policy_arn = pol.get("PolicyArn")
            if policy_name:
                attached_policy_names.append(policy_name)
            if policy_name in HIGH_RISK_MANAGED_POLICIES:
                powerful = True
                policy_reasons.append(f"Attached managed policy: {policy_name}")
            if policy_arn:
                cache_key = f"managed::{policy_arn}"
                if cache_key in policy_doc_cache:
                    pol_powerful, reasons = policy_doc_cache[cache_key]
                else:
                    policy_meta = iam.get_policy(PolicyArn=policy_arn)
                    policy_obj = policy_meta.get("Policy", {}) if isinstance(policy_meta, dict) else {}
                    default_version = policy_obj.get("DefaultVersionId")
                    doc = {}
                    if default_version:
                        version = iam.get_policy_version(PolicyArn=policy_arn, VersionId=default_version)
                        if isinstance(version, dict):
                            doc = version.get("PolicyVersion", {}).get("Document", {})
                    pol_powerful, reasons = _policy_document_is_powerful(doc)
                    policy_doc_cache[cache_key] = (pol_powerful, reasons)
                if pol_powerful:
                    powerful = True
                    for reason in reasons:
                        policy_reasons.append(f"{policy_name or policy_arn}: {reason}")
        if not attached.get("IsTruncated") or not attached.get("Marker"):
            break
        marker = attached.get("Marker")

    inline_policies = iam.list_role_policies(RoleName=role_name).get("PolicyNames", [])
    for inline_name in inline_policies:
        cache_key = f"inline::{role_name}::{inline_name}"
        if cache_key in policy_doc_cache:
            pol_powerful, reasons = policy_doc_cache[cache_key]
        else:
            inline = iam.get_role_policy(RoleName=role_name, PolicyName=inline_name)
            inline_doc = inline.get("PolicyDocument", {}) if isinstance(inline, dict) else {}
            pol_powerful, reasons = _policy_document_is_powerful(inline_doc)
            policy_doc_cache[cache_key] = (pol_powerful, reasons)
        if pol_powerful:
            powerful = True
            for reason in reasons:
                policy_reasons.append(f"Inline {inline_name}: {reason}")

    return {
        "powerful": powerful,
        "policy_reasons": sorted(set(policy_reasons)),
        "attached_policy_names": sorted(set(attached_policy_names)),
        "inline_policy_names": sorted(set(inline_policies)),
    }


def main(botoconfig, session, context=None):
    inputs = collect_inputs()
    target_account_id = (inputs.get("target_account_id") or "").strip()
    iam = session.client("iam", config=botoconfig)
    current_account_id, current_arn = _extract_current_identity(session, botoconfig)
    role_map = _extract_roles_from_dependencies(context)
    trust_map = _extract_trust_from_dependencies(context)
    errors = []

    if not role_map:
        try:
            role_map = _fallback_list_roles(iam)
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as exc:
            return utils.module_result(
                status="error",
                data={"current_arn": current_arn, "current_account_id": current_account_id},
                errors=[f"Failed to enumerate roles: {str(exc)}"],
            )

    role_results = []
    high_risk_roles = []
    policy_doc_cache = {}
    for role_name in sorted(role_map.keys()):
        role_item = role_map.get(role_name, {})
        role_arn = role_item.get("arn")
        try:
            trust_entities = _resolve_role_trust_entities(iam, role_name, trust_map.get(role_name))
            cross_account_entities = []
            wildcard_trust = False
            for ent in trust_entities:
                p_type = ent.get("principal_type")
                value = ent.get("value")
                account_id = _parse_aws_account_from_principal(value)
                if account_id == "*":
                    wildcard_trust = True
                    cross_account_entities.append(
                        {"principal_type": p_type, "value": value, "account_id": "*"}
                    )
                    continue
                if account_id and account_id != current_account_id:
                    if target_account_id and account_id != target_account_id:
                        continue
                    cross_account_entities.append(
                        {"principal_type": p_type, "value": value, "account_id": account_id}
                    )

            policy_scan = _scan_role_policies(iam, role_name, policy_doc_cache=policy_doc_cache)
            has_cross_account_trust = len(cross_account_entities) > 0
            high_risk = bool(policy_scan["powerful"] and has_cross_account_trust)
            if wildcard_trust and policy_scan["powerful"]:
                high_risk = True

            summary_reasons = []
            if has_cross_account_trust:
                summary_reasons.append("Role is assumable by at least one external principal")
            if wildcard_trust:
                summary_reasons.append("Role has wildcard trust")
            summary_reasons.extend(policy_scan["policy_reasons"][:8])

            role_result = {
                "role_name": role_name,
                "role_arn": role_arn,
                "powerful_permissions": policy_scan["powerful"],
                "high_risk": high_risk,
                "cross_account_trust": has_cross_account_trust,
                "cross_account_entities": cross_account_entities,
                "trusted_entity_count": len(trust_entities),
                "attached_policy_names": policy_scan["attached_policy_names"],
                "inline_policy_names": policy_scan["inline_policy_names"],
                "reasons": summary_reasons,
            }
            role_results.append(role_result)
            if high_risk:
                high_risk_roles.append(role_result)
        except (botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError) as exc:
            errors.append(f"Failed to analyze role {role_name}: {str(exc)}")

    role_results.sort(key=lambda x: (not x["high_risk"], not x["cross_account_trust"], x["role_name"]))
    data = {
        "current_arn": current_arn,
        "current_account_id": current_account_id,
        "target_account_id_filter": target_account_id or None,
        "scanned_roles_count": len(role_results),
        "high_risk_roles_count": len(high_risk_roles),
        "roles": role_results,
        "high_risk_roles": high_risk_roles,
    }
    return utils.module_result(data=data, errors=errors)
