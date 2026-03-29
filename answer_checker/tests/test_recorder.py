import duckdb

from answer_checker.recorder import record_success


class TestRecordSuccess:
    def test_writes_parquet_with_correct_schema(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "result.parquet")
        result = record_success(
            "alice",
            1,
            "unused-bucket",
            "eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        assert result == output_path

        rows = duckdb_connection.execute(
            "SELECT name, duckdb_type FROM parquet_schema(?) WHERE duckdb_type IS NOT NULL",
            [output_path],
        ).fetchall()
        column_names = [r[0] for r in rows]
        assert column_names == ["pseudo", "scenario", "solved_at"]

    def test_writes_correct_values(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "result.parquet")
        record_success(
            "bob",
            2,
            "unused-bucket",
            "eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        row = duckdb_connection.execute(
            "SELECT pseudo, scenario FROM read_parquet(?)", [output_path]
        ).fetchone()
        assert row[0] == "bob"
        assert row[1] == 2

    def test_solved_at_is_populated(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "result.parquet")
        record_success(
            "charlie",
            3,
            "unused-bucket",
            "eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        row = duckdb_connection.execute(
            "SELECT solved_at FROM read_parquet(?)", [output_path]
        ).fetchone()
        assert row[0] is not None
