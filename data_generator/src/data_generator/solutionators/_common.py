"""Shared helpers for solutionators: DuckDB connection setup, path helpers."""

from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb

from data_generator.config import CTFConfig
from data_generator.constants import AWS_REGION


def make_duckdb(
    config: CTFConfig,
    *,
    extensions: tuple[str, ...] = (),
    community_extensions: tuple[str, ...] = (),
    s3: bool = False,
    pg: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Build an in-memory DuckDB connection with the requested extensions wired up.

    - extensions: core extensions installed via INSTALL/LOAD (e.g. 'httpfs', 'iceberg', 'postgres').
    - community_extensions: community-repository extensions (e.g. 'http_client').
    - s3: if True, create a SECRET from CTFConfig IAM credentials.
    - pg: if True, ATTACH the project's PostgreSQL DB as alias `postgres_db` (READ_ONLY).
    """
    con = duckdb.connect()

    for ext in extensions:
        con.execute(f"INSTALL {ext}")
        con.execute(f"LOAD {ext}")
    for ext in community_extensions:
        con.execute(f"INSTALL {ext} FROM community")
        con.execute(f"LOAD {ext}")

    if s3:
        # Empty SESSION_TOKEN forces DuckDB to ignore an inherited
        # AWS_SESSION_TOKEN from the environment — IAM-user keys are
        # permanent and don't use a session token.
        con.execute(
            f"""
            CREATE OR REPLACE SECRET ctf_s3 (
                TYPE S3,
                KEY_ID '{config.iam_access_key_id}',
                SECRET '{config.iam_secret_access_key}',
                SESSION_TOKEN '',
                REGION '{AWS_REGION}'
            )
            """
        )

    if pg:
        con.execute(
            f"ATTACH 'host={config.db_host} port={config.db_port} "
            f"dbname={config.db_name} user={config.pg_ro_user} "
            f"password={config.pg_ro_password}' "
            f"AS postgres_db (TYPE POSTGRES, READ_ONLY)"
        )

    return con


def unzip_logs(zip_path: Path, dest_dir: Path) -> Path:
    """Extract a zip archive into dest_dir. Idempotent."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    return dest_dir


def s3_uri(config: CTFConfig, key: str) -> str:
    """Build an s3:// URI for the project bucket."""
    return f"s3://{config.s3_bucket_name}/{key}"


def parse_kv_flag(flag: str) -> dict[str, str]:
    """Parse a comma-separated key=value flag body, e.g.

    ``FLAG{aws_access_key_id=…,aws_secret_access_key=…,bucket=…}`` →
    ``{"aws_access_key_id": "…", "aws_secret_access_key": "…", "bucket": "…"}``
    """
    body = flag.strip()
    if body.startswith("FLAG{") and body.endswith("}"):
        body = body[len("FLAG{"):-1]
    pairs: dict[str, str] = {}
    for part in body.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        pairs[k.strip()] = v.strip()
    return pairs
