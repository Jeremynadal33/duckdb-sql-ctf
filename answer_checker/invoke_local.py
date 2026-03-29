"""Local invocation of the Lambda handler with a real S3 file."""

import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

# Set env vars the handler expects
os.environ.setdefault("BUCKET_NAME", "duckdb-sql-ctf")
os.environ.setdefault("AWS_REGION", "eu-west-1")

from answer_checker.handler import lambda_handler  # noqa: E402


def make_s3_event(bucket: str, key: str) -> dict:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "size": 1059},
                }
            }
        ]
    }


if __name__ == "__main__":
    bucket = sys.argv[1] if len(sys.argv) > 1 else "duckdb-sql-ctf"
    key = sys.argv[2] if len(sys.argv) > 2 else "user-inputs/bueno.parquet"

    event = make_s3_event(bucket, key)
    print(f"Invoking handler with s3://{bucket}/{key}\n")

    result = lambda_handler(event, None)
    print(f"\nResult:\n{json.dumps(result, indent=2)}")
