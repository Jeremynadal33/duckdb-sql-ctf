import logging
import os
from urllib.parse import unquote_plus

import boto3

from answer_checker.event_writer import write_event
from answer_checker.register import _pseudo_exists
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
        logger.info("Schema mismatch for %s", filename)
        write_event(
            action="FLAG_SUBMISSION_REJECTED",
            value={"reason": "schema_mismatch", "filename": filename},
            bucket=bucket_name,
            region=region,
        )
        return {"status": "rejected", "reason": "schema_mismatch", "key": key}

    pseudo, scenario, flag = extract_submission(local_path)
    logger.info("Submission from pseudo=%s, scenario=%d", pseudo, scenario)

    if not _pseudo_exists(pseudo):
        logger.info("Unregistered user: %s", pseudo)
        write_event(
            action="FLAG_SUBMISSION_REJECTED",
            value={"reason": "unregistered_user", "pseudo": pseudo, "scenario": scenario},
            bucket=bucket_name,
            region=region,
        )
        return {"status": "rejected", "reason": "unregistered_user", "key": key}

    answer_key = f"leaderboard/answers/scenario_{scenario}.txt"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=answer_key)
        expected_flag = response["Body"].read().decode("utf-8")
        logger.info("Loaded expected answer from %s", answer_key)
    except s3.exceptions.NoSuchKey:
        logger.error("No answer file found at %s", answer_key)
        write_event(
            action="FLAG_SUBMISSION_REJECTED",
            value={"reason": "unknown_scenario", "pseudo": pseudo, "scenario": scenario},
            bucket=bucket_name,
            region=region,
        )
        return {"status": "rejected", "reason": "unknown_scenario", "key": key}

    if not check_flag(flag, expected_flag):
        logger.info("Wrong flag from pseudo=%s for scenario=%d", pseudo, scenario)
        write_event(
            action="FLAG_SUBMISSION_REJECTED",
            value={"reason": "wrong_flag", "pseudo": pseudo, "scenario": scenario},
            bucket=bucket_name,
            region=region,
        )
        return {"status": "rejected", "reason": "wrong_flag", "key": key}

    output = write_event(
        action="FLAG_SUBMISSION_SUCCESS",
        value={"pseudo": pseudo, "scenario": scenario},
        bucket=bucket_name,
        region=region,
    )
    logger.info("Correct flag! Recorded success for pseudo=%s, scenario=%d at %s", pseudo, scenario, output)
    return {"status": "accepted", "pseudo": pseudo, "scenario": scenario}
