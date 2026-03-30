MODULE_METADATA = {
    "name": "iam_get_account_authorization_details",
    "display_name": "IAM Get Account Authorization Details",
    "category": "enumeration",
    "description": "Enumerate IAM users, groups, roles, and customer managed policies from account authorization details.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

from functions import iam_handler, utils


def help():
    return


def parse_user_details(user_details):
    users = []
    for user in user_details:
        users.append(
            {
                "user_name": user.get("UserName"),
                "user_id": user.get("UserId"),
                "arn": user.get("Arn"),
                "path": user.get("Path"),
                "created": str(user.get("CreateDate")),
                "group_list": user.get("GroupList", []),
                "attached_managed_policies": [
                    policy.get("PolicyName")
                    for policy in user.get("AttachedManagedPolicies", [])
                ],
                "inline_policy_names": [
                    policy.get("PolicyName")
                    for policy in user.get("UserPolicyList", [])
                ],
            }
        )
    return users


def parse_group_details(group_details):
    groups = []
    for group in group_details:
        groups.append(
            {
                "group_name": group.get("GroupName"),
                "group_id": group.get("GroupId"),
                "arn": group.get("Arn"),
                "path": group.get("Path"),
                "attached_managed_policies": [
                    policy.get("PolicyName")
                    for policy in group.get("AttachedManagedPolicies", [])
                ],
                "inline_policy_names": [
                    policy.get("PolicyName")
                    for policy in group.get("GroupPolicyList", [])
                ],
            }
        )
    return groups


def parse_role_details(role_details):
    roles = []
    for role in role_details:
        roles.append(
            {
                "role_name": role.get("RoleName"),
                "role_id": role.get("RoleId"),
                "arn": role.get("Arn"),
                "path": role.get("Path"),
                "created": str(role.get("CreateDate")),
                "instance_profile_list": [
                    profile.get("Arn")
                    for profile in role.get("InstanceProfileList", [])
                ],
                "attached_managed_policies": [
                    policy.get("PolicyName")
                    for policy in role.get("AttachedManagedPolicies", [])
                ],
                "inline_policy_names": [
                    policy.get("PolicyName")
                    for policy in role.get("RolePolicyList", [])
                ],
            }
        )
    return roles


def parse_policy_details(policy_details):
    policies = []
    for policy in policy_details:
        policies.append(
            {
                "policy_name": policy.get("PolicyName"),
                "policy_id": policy.get("PolicyId"),
                "arn": policy.get("Arn"),
                "path": policy.get("Path"),
                "default_version_id": policy.get("DefaultVersionId"),
                "attachment_count": policy.get("AttachmentCount"),
                "is_attachable": policy.get("IsAttachable"),
                "created": str(policy.get("CreateDate")),
                "updated": str(policy.get("UpdateDate")),
            }
        )
    return policies


def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    user_details, group_details, role_details, policy_details = iam.get_account_information()

    users = parse_user_details(user_details)
    groups = parse_group_details(group_details)
    roles = parse_role_details(role_details)
    policies = parse_policy_details(policy_details)

    data = {
        "counts": {
            "users": len(users),
            "groups": len(groups),
            "roles": len(roles),
            "customer_managed_policies": len(policies),
        },
        "users": users,
        "groups": groups,
        "roles": roles,
        "customer_managed_policies": policies,
    }
    return utils.module_result(data=data)
