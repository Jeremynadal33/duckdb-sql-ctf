"""Scenario 4 solutionator — iceberg time-travel scan to recover Quackie's badge metadata."""

from __future__ import annotations

import json
from pathlib import Path

from data_generator.config import CTFConfig
from data_generator.constants import QUACKIE_CHAN_BADGE_ID, QUACKIE_DEATH_DATE
from data_generator.solutionators._common import make_duckdb, s3_uri

SCENARIO4_SQL = """
SELECT metadata FROM iceberg_scan(
    '{warehouse_path}',
    allow_moved_paths = true,
    snapshot_from_timestamp = TIMESTAMP '{snapshot_ts}'
)
WHERE badge_id = '{badge_id}'
"""

SNAPSHOT_TIMESTAMP = QUACKIE_DEATH_DATE.strftime("%Y-%m-%d 00:00:00")


def _warehouse_path(config: CTFConfig, output_dir: Path, local: bool) -> str:
    if local:
        return str(output_dir / "iceberg_warehouse" / "badges" / "badges")
    return s3_uri(config, "data/badges")


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Run scenario 4's iceberg time-travel SQL and return the flag."""
    sql = SCENARIO4_SQL.format(
        warehouse_path=_warehouse_path(config, output_dir, local),
        snapshot_ts=SNAPSHOT_TIMESTAMP,
        badge_id=QUACKIE_CHAN_BADGE_ID,
    )

    con = make_duckdb(
        config, extensions=("iceberg", "httpfs"), s3=not local
    )
    try:
        row = con.execute(sql).fetchone()
    finally:
        con.close()

    if row is None:
        raise AssertionError(f"no iceberg row for badge_id={QUACKIE_CHAN_BADGE_ID}")
    flag = json.loads(row[0])["info"]
    expected = config.flag_scenario4
    assert flag == expected, f"scenario 4 flag mismatch: got {flag!r}, expected {expected!r}"
    return flag
