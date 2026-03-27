import json

import pyarrow.parquet as pq
import pytest

from data_generator.constants import QUACKIE_CHAN_BADGE_ID, QUACKIE_CHAN_EMPLOYEE_ID
from data_generator.generators.scenario2_parquet import (
    NUM_EMPLOYEES,
    _build_badge_flag,
    _build_employee_flag,
    generate_parquet,
)


class TestFlagParts:
    def test_flag_concatenation(self, fake_config):
        part1 = _build_employee_flag(fake_config)
        part2 = _build_badge_flag(fake_config)
        full = part1 + part2
        assert full.startswith("FLAG{")
        assert full.endswith("}")
        assert f"pg_host={fake_config.db_host}" in full
        assert f"pg_password={fake_config.pg_ro_password}" in full
        assert f"pg_dbname={fake_config.db_name}" in full


class TestGenerateParquet:
    @pytest.fixture
    def output_dir(self, fake_config, tmp_path):
        generate_parquet(fake_config, tmp_path)
        return tmp_path

    def test_files_created(self, output_dir):
        assert (output_dir / "employees.parquet").exists()
        assert (output_dir / "badges.parquet").exists()
        assert (output_dir / "departments.parquet").exists()
        assert (output_dir / "README.md").exists()

    def test_employee_count(self, output_dir):
        table = pq.read_table(output_dir / "employees.parquet")
        assert len(table) == NUM_EMPLOYEES

    def test_badge_count(self, output_dir):
        table = pq.read_table(output_dir / "badges.parquet")
        assert len(table) == NUM_EMPLOYEES  # one badge per employee

    def test_department_count(self, output_dir):
        table = pq.read_table(output_dir / "departments.parquet")
        assert len(table) == 10

    def test_quackie_chan_exists(self, output_dir):
        table = pq.read_table(output_dir / "employees.parquet")
        ids = table.column("id").to_pylist()
        assert QUACKIE_CHAN_EMPLOYEE_ID in ids

    def test_quackie_chan_metadata_has_flag(self, fake_config, output_dir):
        table = pq.read_table(output_dir / "employees.parquet")
        for i in range(len(table)):
            if table.column("id")[i].as_py() == QUACKIE_CHAN_EMPLOYEE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert "FLAG{" in meta["info"]
                assert f"pg_host={fake_config.db_host}" in meta["info"]
                return
        pytest.fail("Quackie Chan not found")

    def test_badge_0042_inactive(self, output_dir):
        table = pq.read_table(output_dir / "badges.parquet")
        for i in range(len(table)):
            if table.column("badge_id")[i].as_py() == QUACKIE_CHAN_BADGE_ID:
                assert table.column("status")[i].as_py() == "inactive"
                return
        pytest.fail("BADGE-0042 not found")

    def test_badge_0042_metadata_has_flag(self, fake_config, output_dir):
        table = pq.read_table(output_dir / "badges.parquet")
        for i in range(len(table)):
            if table.column("badge_id")[i].as_py() == QUACKIE_CHAN_BADGE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert f"pg_password={fake_config.pg_ro_password}" in meta["info"]
                return
        pytest.fail("BADGE-0042 not found")

    def test_other_employees_have_noise_metadata(self, output_dir):
        table = pq.read_table(output_dir / "employees.parquet")
        for i in range(len(table)):
            if table.column("id")[i].as_py() != QUACKIE_CHAN_EMPLOYEE_ID:
                meta = json.loads(table.column("metadata")[i].as_py())
                assert "FLAG{" not in meta["info"]
                return  # just check one
