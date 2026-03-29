import os

import boto3
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from moto import mock_aws

BUCKET_NAME = "duckdb-sql-ctf"
EXPECTED_FLAG = "FLAG{test_flag_123}"


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture
def s3_client(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-1")
        client.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        client.put_object(
            Bucket=BUCKET_NAME,
            Key="leaderboard/answers/scenario_1.txt",
            Body=EXPECTED_FLAG.encode(),
        )
        client.put_object(
            Bucket=BUCKET_NAME,
            Key="leaderboard/answers/scenario_2.txt",
            Body="FLAG{scenario_2_flag}".encode(),
        )
        yield client


@pytest.fixture
def duckdb_connection():
    con = duckdb.connect()
    yield con
    con.close()


@pytest.fixture
def valid_parquet(tmp_path) -> str:
    path = str(tmp_path / "valid.parquet")
    table = pa.table(
        {
            "pseudo": ["alice"],
            "scenario": pa.array([1], type=pa.int32()),
            "flag": [EXPECTED_FLAG],
        }
    )
    pq.write_table(table, path)
    return path


@pytest.fixture
def wrong_flag_parquet(tmp_path) -> str:
    path = str(tmp_path / "wrong_flag.parquet")
    table = pa.table(
        {
            "pseudo": ["alice"],
            "scenario": pa.array([1], type=pa.int32()),
            "flag": ["FLAG{wrong}"],
        }
    )
    pq.write_table(table, path)
    return path


@pytest.fixture
def bad_schema_parquet(tmp_path) -> str:
    path = str(tmp_path / "bad_schema.parquet")
    table = pa.table(
        {
            "username": ["alice"],
            "flag": ["FLAG{test}"],
        }
    )
    pq.write_table(table, path)
    return path


@pytest.fixture
def extra_columns_parquet(tmp_path) -> str:
    path = str(tmp_path / "extra.parquet")
    table = pa.table(
        {
            "pseudo": ["alice"],
            "scenario": pa.array([1], type=pa.int32()),
            "flag": [EXPECTED_FLAG],
            "extra": ["data"],
        }
    )
    pq.write_table(table, path)
    return path


@pytest.fixture
def wrong_type_parquet(tmp_path) -> str:
    path = str(tmp_path / "wrong_type.parquet")
    table = pa.table(
        {
            "pseudo": ["alice"],
            "scenario": ["one"],
            "flag": [EXPECTED_FLAG],
        }
    )
    pq.write_table(table, path)
    return path
