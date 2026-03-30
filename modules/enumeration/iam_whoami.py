MODULE_METADATA = {
    "name": "iam_whoami",
    "display_name": "IAM WhoAmI",
    "category": "enumeration",
    "description": "Return the current IAM username and basic identity context.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

from functions import iam_handler, sts_handler, utils


def help():
    return


def main(botoconfig, session):
    iam = iam_handler.IAM(botoconfig, session)
    sts = sts_handler.STS(botoconfig, session)

    username = iam.whoami()
    identity = sts.get_caller_identity()

    data = {
        "username": username,
        "account_id": identity.get("Account"),
        "arn": identity.get("Arn"),
        "user_id": identity.get("UserId"),
    }
    return utils.module_result(data=data)
