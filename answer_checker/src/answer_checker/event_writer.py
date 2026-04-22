import json
import os
import uuid
from datetime import datetime, timezone

import boto3
import duckdb

EXTENSION_DIR = os.environ.get("DUCKDB_EXTENSION_DIR")
EVENTS_PREFIX = "leaderboard/ctf-events"
EVENT_CACHE_CONTROL = "public, max-age=31536000, immutable"


def write_event(
    action: str,
    value: dict,
    bucket: str,
    region: str,
    *,
    connection: duckdb.DuckDBPyConnection | None = None,
    output_path: str | None = None,
) -> str:
    config: dict[str, str | bool | int | float | list[str]] = (
        {"extension_directory": EXTENSION_DIR} if EXTENSION_DIR else {}
    )
    con = connection or duckdb.connect(config=config)
    try:
        ts = datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y%m%dT%H%M%S")
        uid = uuid.uuid4().hex[:8]

        if output_path is not None:
            # Test/override path: write directly without going through S3.
            con.execute(
                f"""
                COPY (
                    SELECT
                        ? AS action,
                        ? AS value,
                        ?::TIMESTAMP AS timestamp
                ) TO '{output_path}' (FORMAT PARQUET)
                """,
                [action, json.dumps(value), ts.isoformat()],
            )
            return output_path

        # Production path: COPY locally, then upload to S3 with Cache-Control so
        # browsers can cache these immutable files indefinitely.
        key = f"{EVENTS_PREFIX}/{action}_{ts_str}_{uid}.parquet"
        local_path = f"/tmp/{action}_{ts_str}_{uid}.parquet"
        con.execute(
            f"""
            COPY (
                SELECT
                    ? AS action,
                    ? AS value,
                    ?::TIMESTAMP AS timestamp
            ) TO '{local_path}' (FORMAT PARQUET)
            """,
            [action, json.dumps(value), ts.isoformat()],
        )
        try:
            boto3.client("s3", region_name=region).upload_file(
                local_path,
                bucket,
                key,
                ExtraArgs={
                    "CacheControl": EVENT_CACHE_CONTROL,
                    "ContentType": "application/vnd.apache.parquet",
                },
            )
        finally:
            try:
                os.remove(local_path)
            except OSError:
                pass
        return f"s3://{bucket}/{key}"
    finally:
        if connection is None:
            con.close()
