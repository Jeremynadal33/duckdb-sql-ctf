import json
import logging
import os

from answer_checker.event_writer import write_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "duckdb-sql-ctf")
REGION = os.environ.get("AWS_REGION", "eu-west-1")

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


def hint_event_handler(event: dict, context: object) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "invalid_json"})

    pseudo = (body.get("pseudo") or "").strip()
    scenario = body.get("scenario")
    hint_title = (body.get("hint_title") or "").strip()

    if not pseudo or scenario is None:
        return _response(400, {"error": "missing_fields", "message": "pseudo and scenario are required."})

    try:
        scenario = int(scenario)
    except (ValueError, TypeError):
        return _response(400, {"error": "invalid_scenario", "message": "scenario must be an integer."})

    try:
        write_event(
            action="HINT_EXPANDED",
            value={"pseudo": pseudo, "scenario": scenario, "hint_title": hint_title},
            bucket=BUCKET_NAME,
            region=REGION,
        )
    except Exception as e:
        logger.error("Failed to write hint event for pseudo=%s scenario=%d: %s", pseudo, scenario, e)
        return _response(500, {"error": "write_failed"})

    logger.info("Hint expanded: pseudo=%s scenario=%d hint=%s", pseudo, scenario, hint_title)
    return _response(200, {"status": "ok"})
