"""Scenario 1 solutionator — read library logs JSON, reconstruct flag from chronological notes."""

from __future__ import annotations

from pathlib import Path

from data_generator.config import CTFConfig
from data_generator.solutionators._common import make_duckdb, unzip_logs

SCENARIO1_SQL = """
WITH data AS (
    SELECT metadata.notes AS flag_part
    FROM read_json('{logs_glob}')
    WHERE timestamp_return IS NULL
      AND document_type = 'acte_de_naissance'
    ORDER BY timestamp_checkout ASC
)
SELECT array_to_string(array_agg(flag_part), '') AS flag FROM data
"""


def _ensure_unziped(config: CTFConfig, output_dir: Path, local: bool) -> Path:
    """Ensure output_dir/unziped exists. When not local, the zip is fetched
    from the bucket's public-read URL — no AWS credentials needed (the player only
    discovers them by solving scenario 1)."""
    zip_path = output_dir / "library_logs.zip"
    if not local:
        import urllib.request

        from data_generator.constants import AWS_REGION

        output_dir.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://{config.s3_bucket_name}.s3.{AWS_REGION}.amazonaws.com"
            "/data/library_logs.zip"
        )
        urllib.request.urlretrieve(url, zip_path)
    return unzip_logs(zip_path, output_dir / "unziped")


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Run scenario 1's canonical SQL and return the reconstructed flag.

    DuckDB cannot read a zip from S3 directly, so the zip is unzipped locally
    in either mode — same flow as a real player.
    """
    from data_generator.generators.scenario1_logs import build_flag

    unziped_dir = _ensure_unziped(config, output_dir, local)
    sql = SCENARIO1_SQL.format(logs_glob=f"{unziped_dir}/*.json")

    con = make_duckdb(config)
    try:
        flag = con.execute(sql).fetchone()[0]
    finally:
        con.close()

    expected = build_flag(config)
    assert flag == expected, f"scenario 1 flag mismatch: got {flag!r}, expected {expected!r}"
    return flag
