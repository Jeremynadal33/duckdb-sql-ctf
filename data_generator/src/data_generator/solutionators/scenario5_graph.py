"""Scenario 5 solutionator — attach the social DuckDB and traverse 2 hops from Quackie."""

from __future__ import annotations

from pathlib import Path

from data_generator.config import CTFConfig
from data_generator.solutionators._common import make_duckdb, s3_uri

ATTACH_SQL = "ATTACH '{db_path}' AS social (READ_ONLY)"

GRAPH_SQL = r"""
WITH quackie AS (
    SELECT id FROM social.main.persons
    WHERE first_name || ' ' || last_name = 'Quackie Chan'
),
first_relations AS (
    SELECT * FROM social.main.relationships
    WHERE person_id_1 = (SELECT id FROM quackie)
),
first_all_ids AS (
    SELECT person_id_1 AS person_id FROM first_relations
    UNION SELECT person_id_2 FROM first_relations
),
second_relations AS (
    SELECT * FROM social.main.relationships
    WHERE person_id_1 IN (SELECT person_id FROM first_all_ids)
),
all_ids AS (
    SELECT person_id FROM first_all_ids
    UNION SELECT person_id_1 FROM second_relations
    UNION SELECT person_id_2 FROM second_relations
)
SELECT regexp_extract(notes, 'FLAG\{[^}]+\}', 0) AS flag
FROM social.main.persons
WHERE id IN (SELECT person_id FROM all_ids)
  AND regexp_extract(notes, 'FLAG\{[^}]+\}', 0) <> ''
"""


def _db_path(config: CTFConfig, output_dir: Path, local: bool) -> str:
    if local:
        return str(output_dir / "network.duckdb")
    return s3_uri(config, "data/network.duckdb")


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Run scenario 5's graph traversal SQL and return Hugh Quackman's flag."""
    con = make_duckdb(config, extensions=("httpfs",), s3=not local)
    try:
        con.execute(ATTACH_SQL.format(db_path=_db_path(config, output_dir, local)))
        row = con.execute(GRAPH_SQL).fetchone()
    finally:
        con.close()

    if row is None:
        raise AssertionError("no flag found in 2-hop neighbourhood of Quackie Chan")
    flag = row[0]
    expected = config.flag_scenario5
    assert flag == expected, f"scenario 5 flag mismatch: got {flag!r}, expected {expected!r}"
    return flag
