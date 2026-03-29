import os
import uuid
from datetime import datetime, timezone

import duckdb

EXTENSION_DIR = os.environ.get("DUCKDB_EXTENSION_DIR")


def record_success(
    pseudo: str,
    scenario: int,
    bucket: str,
    region: str,
    *,
    connection: duckdb.DuckDBPyConnection | None = None,
    output_path: str | None = None,
) -> str:
    config = {"extension_directory": EXTENSION_DIR} if EXTENSION_DIR else {}
    con = connection or duckdb.connect(config=config)
    try:
        if output_path is None:
            con.execute("LOAD httpfs")
            con.execute("SET s3_region = ?", [region])
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            uid = uuid.uuid4().hex[:8]
            output_path = f"s3://{bucket}/leaderboard/results/{pseudo}_{scenario}_{ts}_{uid}.parquet"

        solved_at = datetime.now(timezone.utc).isoformat()
        con.execute(
            f"""
            COPY (
                SELECT
                    ? AS pseudo,
                    ?::INTEGER AS scenario,
                    ?::TIMESTAMP AS solved_at
            ) TO '{output_path}' (FORMAT PARQUET)
            """,
            [pseudo, scenario, solved_at],
        )
        return output_path
    finally:
        if connection is None:
            con.close()
