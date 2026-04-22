"""Scheduled compactor: merges all CTF event parquets into a single snapshot.

Runs on an EventBridge schedule. The frontend reads this snapshot (one HTTP
request, browser-cacheable) plus the handful of event files newer than it,
avoiding a per-event-file scan on every poll.
"""

import logging
import os
import uuid

import boto3
import duckdb

from answer_checker.event_writer import EVENTS_PREFIX

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "duckdb-sql-ctf")
REGION = os.environ.get("AWS_REGION", "eu-west-1")
EXTENSION_DIR = os.environ.get("DUCKDB_EXTENSION_DIR")

SNAPSHOT_KEY = "leaderboard/snapshot.parquet"
SNAPSHOT_CACHE_CONTROL = "public, max-age=15, must-revalidate"


def _configure_duckdb_s3(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("LOAD httpfs")
    con.execute("SET s3_region = ?", [REGION])
    endpoint = os.environ.get("S3_ENDPOINT")
    if endpoint:
        # Test-only path: point httpfs at a local mock S3 (e.g. moto server).
        con.execute("SET s3_endpoint = ?", [endpoint])
        con.execute("SET s3_use_ssl = false")
        con.execute("SET s3_url_style = 'path'")
        con.execute("SET s3_access_key_id = ?", [os.environ.get("AWS_ACCESS_KEY_ID", "testing")])
        con.execute("SET s3_secret_access_key = ?", [os.environ.get("AWS_SECRET_ACCESS_KEY", "testing")])


def _events_prefix_nonempty(s3_client, bucket: str) -> bool:
    resp = s3_client.list_objects_v2(
        Bucket=bucket, Prefix=f"{EVENTS_PREFIX}/", MaxKeys=1
    )
    return resp.get("KeyCount", 0) > 0


def compactor_handler(event: dict, context: object) -> dict:
    endpoint_url = os.environ.get("S3_ENDPOINT")
    boto_kwargs = {"endpoint_url": f"http://{endpoint_url}"} if endpoint_url else {}
    s3_client = boto3.client("s3", region_name=REGION, **boto_kwargs)

    if not _events_prefix_nonempty(s3_client, BUCKET_NAME):
        logger.info("No events to compact under s3://%s/%s/", BUCKET_NAME, EVENTS_PREFIX)
        return {"status": "noop", "reason": "empty_prefix"}

    tmp_key = f"leaderboard/snapshot.tmp.{uuid.uuid4().hex[:8]}.parquet"
    tmp_s3_uri = f"s3://{BUCKET_NAME}/{tmp_key}"
    events_glob = f"s3://{BUCKET_NAME}/{EVENTS_PREFIX}/*.parquet"

    config: dict[str, str | bool | int | float | list[str]] = (
        {"extension_directory": EXTENSION_DIR} if EXTENSION_DIR else {}
    )
    con = duckdb.connect(config=config)
    try:
        _configure_duckdb_s3(con)
        con.execute(
            f"""
            COPY (
                SELECT action, value, timestamp
                FROM read_parquet('{events_glob}', union_by_name=true)
            ) TO '{tmp_s3_uri}' (FORMAT PARQUET)
            """
        )
    finally:
        con.close()

    # Atomic publish from the browser's perspective: GET sees either the old
    # snapshot or the new one, never a partial write. copy_object with
    # MetadataDirective=REPLACE also stamps the immutable Cache-Control.
    s3_client.copy_object(
        Bucket=BUCKET_NAME,
        Key=SNAPSHOT_KEY,
        CopySource={"Bucket": BUCKET_NAME, "Key": tmp_key},
        CacheControl=SNAPSHOT_CACHE_CONTROL,
        ContentType="application/vnd.apache.parquet",
        MetadataDirective="REPLACE",
    )
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=tmp_key)

    logger.info("Published snapshot s3://%s/%s", BUCKET_NAME, SNAPSHOT_KEY)
    return {"status": "ok", "snapshot": f"s3://{BUCKET_NAME}/{SNAPSHOT_KEY}"}
