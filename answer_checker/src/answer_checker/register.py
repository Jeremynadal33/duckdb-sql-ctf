import json
import logging
import os
import re
from datetime import datetime, timezone

import duckdb

from answer_checker.event_writer import EVENTS_PREFIX, write_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "duckdb-sql-ctf")
REGION = os.environ.get("AWS_REGION", "eu-west-1")
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


def _pseudo_exists(pseudo: str) -> bool:
    config: dict[str, str | bool | int | float | list[str]] = (
        {"extension_directory": EXTENSION_DIR} if EXTENSION_DIR else {}
    )
    con = duckdb.connect(config=config)
    try:
        con.execute("LOAD httpfs")
        con.execute("SET s3_region = ?", [REGION])
        glob_path = f"s3://{BUCKET_NAME}/{EVENTS_PREFIX}/REGISTRATION_*.parquet"
        result = con.execute(
            f"""
            SELECT COUNT(*) FROM read_parquet('{glob_path}', union_by_name=true)
            WHERE action = 'REGISTRATION'
              AND json_extract_string(value, '$.pseudo') = ?
            """,
            [pseudo],
        ).fetchone()
        return result is not None and result[0] > 0
    except Exception as e:
        if "No files found" in str(e):
            return False
        raise
    finally:
        con.close()


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

    try:
        if _pseudo_exists(pseudo):
            logger.info("Pseudo already taken: %s", pseudo)
            return _response(409, {"error": "pseudo_taken", "message": "Ce pseudo est deja pris."})
    except Exception as e:
        logger.error("Error checking pseudo existence: %s", e)
        return _response(500, {"error": "internal_error"})

    try:
        write_event(
            action="REGISTRATION",
            value={"pseudo": pseudo},
            bucket=BUCKET_NAME,
            region=REGION,
        )
    except Exception as e:
        logger.error("Failed to write event for pseudo=%s: %s", pseudo, e)
        return _response(500, {"error": "write_failed"})

    created_at = datetime.now(timezone.utc).isoformat()
    logger.info("Registered pseudo=%s at %s", pseudo, created_at)
    return _response(201, {"pseudo": pseudo, "created_at": created_at})
