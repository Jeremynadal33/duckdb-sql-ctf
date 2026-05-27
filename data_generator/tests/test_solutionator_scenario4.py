import json

import duckdb

from data_generator.constants import (
    NUM_ICEBERG_SNAPSHOTS,
    QUACKIE_CHAN_BADGE_ID,
)
from data_generator.generators.scenario4_iceberg import generate_iceberg
from data_generator.solutionators.scenario4_iceberg import solve


def test_solve_returns_canonical_flag(fake_config, tmp_path):
    generate_iceberg(fake_config, tmp_path, upload=False)
    flag = solve(fake_config, tmp_path, local=True)
    assert flag == fake_config.flag_scenario4


def test_read_parquet_bypass_returns_only_decoys(fake_config, tmp_path):
    """A naive read_parquet attack should see many FLAG{...} candidates,
    with the real flag drowned among indistinguishable decoys."""
    generate_iceberg(fake_config, tmp_path, upload=False)

    data_glob = str(
        tmp_path / "iceberg_warehouse" / "badges" / "badges" / "data" / "*.parquet"
    )
    con = duckdb.connect()
    rows = con.execute(
        f"SELECT metadata FROM read_parquet('{data_glob}') "
        f"WHERE badge_id = '{QUACKIE_CHAN_BADGE_ID}'"
    ).fetchall()
    con.close()

    infos = [json.loads(r[0])["info"] for r in rows]
    flag_like = [s for s in infos if s.startswith("FLAG{")]

    # 1 real flag + (NUM_ICEBERG_SNAPSHOTS - 1) decoys, all FLAG-shaped.
    assert len(flag_like) == NUM_ICEBERG_SNAPSHOTS, (
        f"expected {NUM_ICEBERG_SNAPSHOTS} FLAG-like rows, got {len(flag_like)}"
    )
    assert infos.count(fake_config.flag_scenario4) == 1, (
        "real flag should appear in exactly one Quackie row"
    )
    decoys = [s for s in flag_like if s != fake_config.flag_scenario4]
    assert len(decoys) == NUM_ICEBERG_SNAPSHOTS - 1
    assert fake_config.flag_scenario4 not in decoys
