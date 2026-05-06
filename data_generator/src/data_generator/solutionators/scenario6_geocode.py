"""Scenario 6 solutionator — same chain as scenario 3, but for Hugh Quackman (Paris)."""

from __future__ import annotations

from pathlib import Path

from data_generator.config import CTFConfig
from data_generator.solutionators._common import make_duckdb
from data_generator.solutionators.scenario3_postgres import solve_pg_geocode


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Find Hugh Quackman in PG, geocode his current address (Paris), read note_cachee.

    Scenario 6 always hits live PostgreSQL + live Nominatim — ``local`` and
    ``output_dir`` are accepted for API symmetry but ignored.
    """

    con = make_duckdb(
        config,
        extensions=("postgres",),
        community_extensions=("http_client",),
        pg=True,
    )
    try:
        result = solve_pg_geocode(con, "Hugh", "Quackman")
    finally:
        con.close()

    flag = result["metadata"]["note_cachee"]
    expected = config.flag_scenario6
    assert flag == expected, f"scenario 6 flag mismatch: got {flag!r}, expected {expected!r}"
    return flag
