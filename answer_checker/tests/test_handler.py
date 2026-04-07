import os
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
from moto import mock_aws

from tests.conftest import BUCKET_NAME, EXPECTED_FLAG


def _make_s3_event(bucket: str, key: str) -> dict:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key},
                }
            }
        ]
    }


class TestHandler:
    @mock_aws
    def test_correct_submission(self, s3_client, valid_parquet):
        s3_client.upload_file(valid_parquet, BUCKET_NAME, "user-inputs/test.parquet")

        with (
            patch.dict(os.environ, {"BUCKET_NAME": BUCKET_NAME, "AWS_REGION": "eu-west-1"}),
            patch("answer_checker.handler.write_event", return_value="s3://mock/event.parquet") as mock_write,
            patch("answer_checker.handler._pseudo_exists", return_value=True),
            patch("answer_checker.handler.s3", s3_client),
        ):
            from answer_checker.handler import lambda_handler

            result = lambda_handler(
                _make_s3_event(BUCKET_NAME, "user-inputs/test.parquet"), None
            )

        assert result["status"] == "accepted"
        assert result["pseudo"] == "alice"
        assert result["scenario"] == 1
        mock_write.assert_called_once_with(
            action="FLAG_SUBMISSION_SUCCESS",
            value={"pseudo": "alice", "scenario": 1},
            bucket=BUCKET_NAME,
            region="eu-west-1",
        )

    @mock_aws
    def test_bad_schema_rejected(self, s3_client, bad_schema_parquet):
        s3_client.upload_file(bad_schema_parquet, BUCKET_NAME, "user-inputs/bad.parquet")

        with (
            patch.dict(os.environ, {"BUCKET_NAME": BUCKET_NAME, "AWS_REGION": "eu-west-1"}),
            patch("answer_checker.handler.write_event") as mock_write,
            patch("answer_checker.handler.s3", s3_client),
        ):
            from answer_checker.handler import lambda_handler

            result = lambda_handler(
                _make_s3_event(BUCKET_NAME, "user-inputs/bad.parquet"), None
            )

        assert result["status"] == "rejected"
        assert result["reason"] == "schema_mismatch"
        mock_write.assert_called_once()
        assert mock_write.call_args.kwargs["action"] == "FLAG_SUBMISSION_REJECTED"

    @mock_aws
    def test_unregistered_user_rejected(self, s3_client, valid_parquet):
        s3_client.upload_file(valid_parquet, BUCKET_NAME, "user-inputs/test.parquet")

        with (
            patch.dict(os.environ, {"BUCKET_NAME": BUCKET_NAME, "AWS_REGION": "eu-west-1"}),
            patch("answer_checker.handler.write_event") as mock_write,
            patch("answer_checker.handler._pseudo_exists", return_value=False),
            patch("answer_checker.handler.s3", s3_client),
        ):
            from answer_checker.handler import lambda_handler

            result = lambda_handler(
                _make_s3_event(BUCKET_NAME, "user-inputs/test.parquet"), None
            )

        assert result["status"] == "rejected"
        assert result["reason"] == "unregistered_user"
        mock_write.assert_called_once()
        assert mock_write.call_args.kwargs["action"] == "FLAG_SUBMISSION_REJECTED"

    @mock_aws
    def test_wrong_flag_rejected(self, s3_client, wrong_flag_parquet):
        s3_client.upload_file(
            wrong_flag_parquet, BUCKET_NAME, "user-inputs/wrong.parquet"
        )

        with (
            patch.dict(os.environ, {"BUCKET_NAME": BUCKET_NAME, "AWS_REGION": "eu-west-1"}),
            patch("answer_checker.handler.write_event") as mock_write,
            patch("answer_checker.handler._pseudo_exists", return_value=True),
            patch("answer_checker.handler.s3", s3_client),
        ):
            from answer_checker.handler import lambda_handler

            result = lambda_handler(
                _make_s3_event(BUCKET_NAME, "user-inputs/wrong.parquet"), None
            )

        assert result["status"] == "rejected"
        assert result["reason"] == "wrong_flag"
        mock_write.assert_called_once()
        assert mock_write.call_args.kwargs["action"] == "FLAG_SUBMISSION_REJECTED"

    @mock_aws
    def test_unknown_scenario_rejected(self, s3_client, tmp_path):
        path = str(tmp_path / "unknown_scenario.parquet")
        table = pa.table(
            {
                "pseudo": ["alice"],
                "scenario": pa.array([99], type=pa.int32()),
                "flag": ["FLAG{whatever}"],
            }
        )
        pq.write_table(table, path)
        s3_client.upload_file(path, BUCKET_NAME, "user-inputs/unknown.parquet")

        with (
            patch.dict(os.environ, {"BUCKET_NAME": BUCKET_NAME, "AWS_REGION": "eu-west-1"}),
            patch("answer_checker.handler.write_event") as mock_write,
            patch("answer_checker.handler._pseudo_exists", return_value=True),
            patch("answer_checker.handler.s3", s3_client),
        ):
            from answer_checker.handler import lambda_handler

            result = lambda_handler(
                _make_s3_event(BUCKET_NAME, "user-inputs/unknown.parquet"), None
            )

        assert result["status"] == "rejected"
        assert result["reason"] == "unknown_scenario"
        mock_write.assert_called_once()
        assert mock_write.call_args.kwargs["action"] == "FLAG_SUBMISSION_REJECTED"
