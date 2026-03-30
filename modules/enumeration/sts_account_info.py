MODULE_METADATA = {
    "name": "sts_account_info",
    "display_name": "STS Account Info",
    "category": "enumeration",
    "description": "Get account-level identity details from STS caller identity.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

from functions import sts_handler, utils


def help():
    return


def main(botoconfig, session):
    sts = sts_handler.STS(botoconfig, session)
    identity = sts.get_caller_identity()
    return utils.module_result(
        data={
            "account_id": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }
    )
