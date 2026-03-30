MODULE_METADATA = {
    "name": "iam_enumerate_users",
    "display_name": "IAM Enumerate Users",
    "category": "enumeration",
    "description": "Enumerate IAM users in the current AWS account.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

from functions import iam_handler, utils


def help():
    return


def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    response = iam.enumerate_users()

    users = []
    for user in response.get("Users", []):
        users.append(
            {
                "user_name": user.get("UserName"),
                "arn": user.get("Arn"),
                "user_id": user.get("UserId"),
                "created": str(user.get("CreateDate")),
            }
        )

    data = {
        "count": len(users),
        "users": users,
    }
    return utils.module_result(data=data)
