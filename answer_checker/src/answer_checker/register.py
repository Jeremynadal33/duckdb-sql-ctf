import json
import logging
import os
import re
from datetime import datetime, timezone

import boto3
import duckdb

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET_NAME = os.environ.get("BUCKET_NAME", "duckdb-sql-ctf")
REGION = os.environ.get("AWS_REGION", "eu-west-1")
USERS_PREFIX = "leaderboard/users"
EXTENSION_DIR = os.environ.get("DUCKDB_EXTENSION_DIR")

PSEUDO_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Content-Type": "application/json",
}


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def register_handler(event: dict, context: object) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "invalid_json"})

    pseudo = (body.get("pseudo") or "").strip().lower()

    if not pseudo or not PSEUDO_RE.match(pseudo):
        return _response(400, {
            "error": "invalid_pseudo",
            "message": "Le pseudo doit contenir entre 3 et 20 caracteres (lettres, chiffres, _ ou -).",
        })

    key = f"{USERS_PREFIX}/{pseudo}.parquet"

    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=key)
        logger.info("Pseudo already taken: %s", pseudo)
        return _response(409, {"error": "pseudo_taken", "message": "Ce pseudo est deja pris."})
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "404":
            logger.error("S3 head_object error: %s", e)
            return _response(500, {"error": "internal_error"})

    created_at = datetime.now(timezone.utc).isoformat()

    config = {"extension_directory": EXTENSION_DIR} if EXTENSION_DIR else {}
    con = duckdb.connect(config=config)
    try:
        con.execute("LOAD httpfs")
        con.execute("SET s3_region = ?", [REGION])
        output_path = f"s3://{BUCKET_NAME}/{key}"
        con.execute(
            f"""
            COPY (
                SELECT
                    ? AS pseudo,
                    ?::TIMESTAMP AS created_at
            ) TO '{output_path}' (FORMAT PARQUET)
            """,
            [pseudo, created_at],
        )
    except Exception as e:
        logger.error("Failed to write parquet for pseudo=%s: %s", pseudo, e)
        return _response(500, {"error": "write_failed"})
    finally:
        con.close()

    logger.info("Registered pseudo=%s at %s", pseudo, created_at)
    return _response(201, {"pseudo": pseudo, "created_at": created_at})
