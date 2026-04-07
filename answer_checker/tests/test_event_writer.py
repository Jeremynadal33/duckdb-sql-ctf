import json

import duckdb

from answer_checker.event_writer import write_event


class TestWriteEvent:
    def test_writes_parquet_with_correct_schema(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "event.parquet")
        result = write_event(
            action="FLAG_SUBMISSION_SUCCESS",
            value={"pseudo": "alice", "scenario": 1},
            bucket="unused-bucket",
            region="eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        assert result == output_path

        rows = duckdb_connection.execute(
            "SELECT name, duckdb_type FROM parquet_schema(?) WHERE duckdb_type IS NOT NULL",
            [output_path],
        ).fetchall()
        column_names = [r[0] for r in rows]
        assert column_names == ["action", "value", "timestamp"]

    def test_writes_correct_values(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "event.parquet")
        write_event(
            action="FLAG_SUBMISSION_SUCCESS",
            value={"pseudo": "bob", "scenario": 2},
            bucket="unused-bucket",
            region="eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        row = duckdb_connection.execute(
            "SELECT action, value FROM read_parquet(?)", [output_path]
        ).fetchone()
        assert row[0] == "FLAG_SUBMISSION_SUCCESS"
        parsed = json.loads(row[1])
        assert parsed["pseudo"] == "bob"
        assert parsed["scenario"] == 2

    def test_timestamp_is_populated(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "event.parquet")
        write_event(
            action="REGISTRATION",
            value={"pseudo": "charlie"},
            bucket="unused-bucket",
            region="eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        row = duckdb_connection.execute(
            "SELECT timestamp FROM read_parquet(?)", [output_path]
        ).fetchone()
        assert row[0] is not None

    def test_rejection_event(self, tmp_path, duckdb_connection):
        output_path = str(tmp_path / "event.parquet")
        write_event(
            action="FLAG_SUBMISSION_REJECTED",
            value={"reason": "wrong_flag", "pseudo": "alice", "scenario": 1},
            bucket="unused-bucket",
            region="eu-west-1",
            connection=duckdb_connection,
            output_path=output_path,
        )
        row = duckdb_connection.execute(
            "SELECT action, value FROM read_parquet(?)", [output_path]
        ).fetchone()
        assert row[0] == "FLAG_SUBMISSION_REJECTED"
        parsed = json.loads(row[1])
        assert parsed["reason"] == "wrong_flag"
