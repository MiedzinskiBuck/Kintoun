MODULE_METADATA = {
    "name": "iam_enumerate_roles",
    "display_name": "IAM Enumerate Roles",
    "category": "enumeration",
    "description": "Enumerate IAM roles in the current AWS account.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
    "result_view": "iam_enumerate_roles",
}

from functions import iam_handler, utils


def help():
    return


def parse_roles(response):
    roles = []
    for role in response.get("Roles", []):
        roles.append(
            {
                "role_name": role.get("RoleName"),
                "arn": role.get("Arn"),
                "role_id": role.get("RoleId"),
                "path": role.get("Path"),
                "description": role.get("Description"),
                "max_session_duration": role.get("MaxSessionDuration"),
                "created": str(role.get("CreateDate")),
            }
        )
    return roles


def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)

    response = iam.enumerate_roles()
    roles = parse_roles(response)

    while response.get("IsTruncated") and response.get("Marker"):
        response = iam.enumerate_roles(marker=response.get("Marker"))
        roles.extend(parse_roles(response))

    data = {
        "count": len(roles),
        "roles": roles,
    }
    return utils.module_result(data=data)
