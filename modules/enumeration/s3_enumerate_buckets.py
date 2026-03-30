MODULE_METADATA = {
    "name": "s3_enumerate_buckets",
    "display_name": "S3 Enumerate Buckets",
    "category": "enumeration",
    "description": "Enumerate S3 buckets and return bucket-level metadata.",
    "requires_region": False,
    "inputs": [],
    "output_type": "json",
    "risk_level": "low",
}

from functions import s3_handler, utils


def help():
    return


def main(botoconfig, session):
    s3 = s3_handler.S3(botoconfig, session)
    bucket_data = s3.list_buckets()
    if not bucket_data:
        return utils.module_result(status="error", data={"count": 0, "buckets": []}, errors=["Failed to list buckets"])

    buckets = []
    for bucket in bucket_data.get("Buckets", []):
        buckets.append(
            {
                "name": bucket.get("Name"),
                "created": str(bucket.get("CreationDate")),
            }
        )

    return utils.module_result(
        data={
            "count": len(buckets),
            "buckets": buckets,
        }
    )
