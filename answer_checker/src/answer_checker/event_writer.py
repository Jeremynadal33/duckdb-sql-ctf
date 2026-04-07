import json
import os
import uuid
from datetime import datetime, timezone

import duckdb

EXTENSION_DIR = os.environ.get("DUCKDB_EXTENSION_DIR")
EVENTS_PREFIX = "leaderboard/ctf-events"


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
        if output_path is None:
            con.execute("LOAD httpfs")
            con.execute("SET s3_region = ?", [region])
            ts_str = ts.strftime("%Y%m%dT%H%M%S")
            uid = uuid.uuid4().hex[:8]
            output_path = f"s3://{bucket}/{EVENTS_PREFIX}/{action}_{ts_str}_{uid}.parquet"

        value_json = json.dumps(value)
        con.execute(
            f"""
            COPY (
                SELECT
                    ? AS action,
                    ? AS value,
                    ?::TIMESTAMP AS timestamp
            ) TO '{output_path}' (FORMAT PARQUET)
            """,
            [action, value_json, ts.isoformat()],
        )
        return output_path
    finally:
        if connection is None:
            con.close()
