"""Scenario 2 solutionator — fuzzy-match library borrowers against the employees parquet."""

from __future__ import annotations

from pathlib import Path

from data_generator.config import CTFConfig
from data_generator.constants import QUACKIE_CHAN_EMPLOYEE_ID
from data_generator.solutionators._common import make_duckdb, s3_uri
from data_generator.solutionators.scenario1_logs import _ensure_unziped

SCENARIO2_SQL = """
WITH identities AS (
    SELECT *
    FROM read_json('{logs_glob}')
    WHERE timestamp_return IS NULL
      AND document_type = 'acte_de_naissance'
),
similar_employees AS (
    SELECT
        jaro_winkler_similarity(
            i.borrower_name, e.first_name || ' ' || e.last_name
        ) AS score,
        i.borrower_name,
        e.*
    FROM read_parquet('{employees_glob}') AS e
    CROSS JOIN identities AS i
    WHERE score > 0.8
)
SELECT DISTINCT
    id,
    first_name,
    last_name,
    json(metadata).info AS info
FROM similar_employees
"""


def _employees_glob(config: CTFConfig, output_dir: Path, local: bool) -> str:
    if local:
        return f"{output_dir}/employees/*.parquet"
    return s3_uri(config, "data/employees/*.parquet")


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Run scenario 2's canonical SQL and return Quackie Chan's employee flag."""
    from data_generator.generators.scenario2_parquet import build_employee_flag

    unziped_dir = _ensure_unziped(config, output_dir, local)
    sql = SCENARIO2_SQL.format(
        logs_glob=f"{unziped_dir}/*.json",
        employees_glob=_employees_glob(config, output_dir, local),
    )

    con = make_duckdb(config, extensions=("httpfs",), s3=not local)
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()

    quackie = next(
        (r for r in rows if r[0] == QUACKIE_CHAN_EMPLOYEE_ID), None
    )
    if quackie is None:
        raise AssertionError(
            f"Quackie Chan (id={QUACKIE_CHAN_EMPLOYEE_ID}) not found in fuzzy matches: {rows!r}"
        )
    info = quackie[3]
    if isinstance(info, str) and info.startswith('"') and info.endswith('"'):
        info = info[1:-1]

    expected = build_employee_flag(config)
    assert info == expected, f"scenario 2 flag mismatch: got {info!r}, expected {expected!r}"
    return info
