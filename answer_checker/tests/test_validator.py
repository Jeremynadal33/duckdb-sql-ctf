import pyarrow as pa
import pyarrow.parquet as pq

from answer_checker.validator import check_flag, extract_submission, validate_schema


class TestValidateSchema:
    def test_valid_schema(self, valid_parquet):
        assert validate_schema(valid_parquet) is True

    def test_wrong_column_names(self, bad_schema_parquet):
        assert validate_schema(bad_schema_parquet) is False

    def test_extra_columns(self, extra_columns_parquet):
        assert validate_schema(extra_columns_parquet) is False

    def test_wrong_column_types(self, wrong_type_parquet):
        assert validate_schema(wrong_type_parquet) is False

    def test_missing_columns(self, tmp_path):
        path = str(tmp_path / "missing.parquet")
        table = pa.table({"pseudo": ["alice"], "flag": ["FLAG{x}"]})
        pq.write_table(table, path)
        assert validate_schema(path) is False


class TestExtractSubmission:
    def test_extract_valid(self, valid_parquet):
        pseudo, scenario, flag = extract_submission(valid_parquet)
        assert pseudo == "alice"
        assert scenario == 1
        assert flag == "FLAG{test_flag_123}"

    def test_empty_parquet(self, tmp_path):
        path = str(tmp_path / "empty.parquet")
        schema = pa.schema(
            [
                ("pseudo", pa.string()),
                ("scenario", pa.int32()),
                ("flag", pa.string()),
            ]
        )
        table = pa.table(
            {"pseudo": [], "scenario": pa.array([], type=pa.int32()), "flag": []},
            schema=schema,
        )
        pq.write_table(table, path)
        try:
            extract_submission(path)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestCheckFlag:
    def test_exact_match(self):
        assert check_flag("FLAG{abc}", "FLAG{abc}") is True

    def test_mismatch(self):
        assert check_flag("FLAG{abc}", "FLAG{xyz}") is False

    def test_whitespace_trimmed(self):
        assert check_flag("FLAG{abc}\n", "FLAG{abc}") is True
        assert check_flag("FLAG{abc}", "  FLAG{abc}  ") is True
