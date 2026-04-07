import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from data_generator.constants import QUACKIE_CHAN_BADGE_ID, QUACKIE_CHAN_EMPLOYEE_ID
from data_generator.generators.scenario2_parquet import (
    NUM_EMPLOYEES,
    _build_employee_flag,
    generate_parquet,
)


def _read_chunked_table(output_dir: Path, table_name: str) -> pa.Table:
    """Read all parquet chunks from a subdirectory and concatenate."""
    table_dir = output_dir / table_name
    tables = [pq.read_table(f) for f in sorted(table_dir.glob("*.parquet"))]
    return pa.concat_tables(tables)


class TestFlagParts:
    def test_full_flag_in_employee(self, fake_config):
        flag = _build_employee_flag(fake_config)
        assert flag.startswith("FLAG{")
        assert flag.endswith("}")
        assert f"pg_host={fake_config.db_host}" in flag
        assert f"pg_password={fake_config.pg_ro_password}" in flag
        assert f"pg_dbname={fake_config.db_name}" in flag


class TestGenerateParquet:
    @pytest.fixture
    def output_dir(self, fake_config, tmp_path):
        generate_parquet(fake_config, tmp_path)
        return tmp_path

    def test_files_created(self, output_dir):
        assert (output_dir / "employees").is_dir()
        assert (output_dir / "badges").is_dir()
        assert (output_dir / "departments").is_dir()
        assert list((output_dir / "employees").glob("*.parquet"))
        assert list((output_dir / "badges").glob("*.parquet"))
        assert list((output_dir / "departments").glob("*.parquet"))
        assert (output_dir / "README.md").exists()

    def test_employees_have_multiple_chunks(self, output_dir):
        chunks = list((output_dir / "employees").glob("*.parquet"))
        assert len(chunks) >= 3

    def test_badges_have_multiple_chunks(self, output_dir):
        chunks = list((output_dir / "badges").glob("*.parquet"))
        assert len(chunks) >= 3

    def test_departments_have_multiple_chunks(self, output_dir):
        chunks = list((output_dir / "departments").glob("*.parquet"))
        assert len(chunks) >= 2

    def test_employee_count(self, output_dir):
        table = _read_chunked_table(output_dir, "employees")
        assert len(table) == NUM_EMPLOYEES

    def test_badge_count(self, output_dir):
        table = _read_chunked_table(output_dir, "badges")
        assert len(table) == NUM_EMPLOYEES  # one badge per employee

    def test_department_count(self, output_dir):
        table = _read_chunked_table(output_dir, "departments")
        assert len(table) == 10

    def test_quackie_chan_exists(self, output_dir):
        table = _read_chunked_table(output_dir, "employees")
        ids = table.column("id").to_pylist()
        assert QUACKIE_CHAN_EMPLOYEE_ID in ids

    def test_quackie_chan_metadata_has_full_flag(self, fake_config, output_dir):
        table = _read_chunked_table(output_dir, "employees")
        for i in range(len(table)):
            if table.column("id")[i].as_py() == QUACKIE_CHAN_EMPLOYEE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert "FLAG{" in meta["info"]
                assert f"pg_host={fake_config.db_host}" in meta["info"]
                assert f"pg_password={fake_config.pg_ro_password}" in meta["info"]
                assert f"pg_dbname={fake_config.db_name}" in meta["info"]
                return
        pytest.fail("Quackie Chan not found")

    def test_badge_0042_inactive(self, output_dir):
        table = _read_chunked_table(output_dir, "badges")
        for i in range(len(table)):
            if table.column("badge_id")[i].as_py() == QUACKIE_CHAN_BADGE_ID:
                assert table.column("status")[i].as_py() == "inactive"
                return
        pytest.fail("BADGE-0042 not found")

    def test_badge_0042_metadata_has_no_flag(self, output_dir):
        table = _read_chunked_table(output_dir, "badges")
        for i in range(len(table)):
            if table.column("badge_id")[i].as_py() == QUACKIE_CHAN_BADGE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert "FLAG{" not in meta["info"]
                return
        pytest.fail("BADGE-0042 not found")

    def test_other_employees_have_noise_metadata(self, output_dir):
        table = _read_chunked_table(output_dir, "employees")
        for i in range(len(table)):
            if table.column("id")[i].as_py() != QUACKIE_CHAN_EMPLOYEE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert "FLAG{" not in meta["info"]
                return  # just check one
