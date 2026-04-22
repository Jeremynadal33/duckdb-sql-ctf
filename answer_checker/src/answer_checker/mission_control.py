import json
import logging
import os

from answer_checker.event_writer import write_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "duckdb-sql-ctf")
REGION = os.environ.get("AWS_REGION", "eu-west-1")
ADMIN_PSEUDO = os.environ.get("ADMIN_PSEUDO", "adminpj")

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


def mission_control_handler(event: dict, context: object) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "invalid_json"})

    pseudo = (body.get("pseudo") or "").strip()
    end_time_ms = body.get("end_time_ms")

    if not pseudo:
        return _response(400, {"error": "missing_fields", "message": "pseudo is required."})

    if pseudo.lower() != ADMIN_PSEUDO.lower():
        return _response(403, {"error": "forbidden", "message": "Admin only."})

    if end_time_ms is None:
        return _response(400, {"error": "missing_fields", "message": "end_time_ms is required."})

    try:
        end_time_ms = int(end_time_ms)
    except (ValueError, TypeError):
        return _response(400, {"error": "invalid_end_time_ms", "message": "end_time_ms must be an integer."})

    try:
        write_event(
            action="MISSION_CONTROL",
            value={"activated_by": pseudo, "end_time_ms": end_time_ms},
            bucket=BUCKET_NAME,
            region=REGION,
        )
    except Exception as e:
        logger.error("Failed to write mission control event: pseudo=%s error=%s", pseudo, e)
        return _response(500, {"error": "write_failed"})

    logger.info("Mission activated: pseudo=%s end_time_ms=%d", pseudo, end_time_ms)
    return _response(200, {"status": "ok", "end_time_ms": end_time_ms})
