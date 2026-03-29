import logging
import os
from urllib.parse import unquote_plus

import boto3

from answer_checker.recorder import record_success
from answer_checker.validator import check_flag, extract_submission, validate_schema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event: dict, context: object) -> dict:
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    size = record["s3"]["object"].get("size", "unknown")
    filename = key.rsplit("/", 1)[-1]

    bucket_name = os.environ.get("BUCKET_NAME", bucket)
    region = os.environ.get("AWS_REGION", "eu-west-1")

    logger.info("Received upload: s3://%s/%s (size=%s, filename=%s)", bucket, key, size, filename)

    local_path = f"/tmp/{filename}"
    s3.download_file(bucket, key, local_path)
    logger.info("Downloaded to %s", local_path)

    if not validate_schema(local_path):
        dlq_key = f"leaderboard/dead-letter-queue/{filename}"
        logger.info("Schema mismatch for %s, copying to %s", filename, dlq_key)
        s3.copy_object(
            Bucket=bucket_name,
            Key=dlq_key,
            CopySource={"Bucket": bucket, "Key": key},
        )
        return {"status": "rejected", "reason": "schema_mismatch", "key": key}

    pseudo, scenario, flag = extract_submission(local_path)
    logger.info("Submission from pseudo=%s, scenario=%d", pseudo, scenario)

    answer_key = f"leaderboard/answers/scenario_{scenario}.txt"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=answer_key)
        expected_flag = response["Body"].read().decode("utf-8")
        logger.info("Loaded expected answer from %s", answer_key)
    except s3.exceptions.NoSuchKey:
        dlq_key = f"leaderboard/dead-letter-queue/{filename}"
        logger.error("No answer file found at %s, copying to %s", answer_key, dlq_key)
        s3.copy_object(
            Bucket=bucket_name,
            Key=dlq_key,
            CopySource={"Bucket": bucket, "Key": key},
        )
        return {"status": "rejected", "reason": "unknown_scenario", "key": key}

    if not check_flag(flag, expected_flag):
        dlq_key = f"leaderboard/dead-letter-queue/{filename}"
        logger.info("Wrong flag from pseudo=%s for scenario=%d, copying to %s", pseudo, scenario, dlq_key)
        s3.copy_object(
            Bucket=bucket_name,
            Key=dlq_key,
            CopySource={"Bucket": bucket, "Key": key},
        )
        return {"status": "rejected", "reason": "wrong_flag", "key": key}

    output = record_success(pseudo, scenario, bucket_name, region)
    logger.info("Correct flag! Recorded success for pseudo=%s, scenario=%d at %s", pseudo, scenario, output)
    return {"status": "accepted", "pseudo": pseudo, "scenario": scenario}
