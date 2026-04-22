import json
import os
import socket
from unittest.mock import patch

import boto3
import duckdb
import pytest
from botocore.exceptions import ClientError
from moto.server import ThreadedMotoServer

from answer_checker.compactor import (
    SNAPSHOT_CACHE_CONTROL,
    SNAPSHOT_KEY,
    compactor_handler,
)
from tests.conftest import BUCKET_NAME


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def moto_s3():
    """Real HTTP moto server so DuckDB's httpfs can talk S3 to it."""
    port = _free_port()
    server = ThreadedMotoServer(port=port, verbose=False)
    server.start()
    endpoint = f"127.0.0.1:{port}"

    env = {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "eu-west-1",
        "S3_ENDPOINT": endpoint,
        "BUCKET_NAME": BUCKET_NAME,
    }
    with patch.dict(os.environ, env):
        client = boto3.client(
            "s3",
            region_name="eu-west-1",
            endpoint_url=f"http://{endpoint}",
        )
        try:
            client.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                raise
        # Moto backends are process-global; drop any objects from a previous test.
        listing = client.list_objects_v2(Bucket=BUCKET_NAME)
        for obj in listing.get("Contents", []):
            client.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
        try:
            yield client
        finally:
            server.stop()


def _write_event_parquet(tmp_path, filename: str, action: str, value: dict) -> str:
    path = str(tmp_path / filename)
    con = duckdb.connect()
    # Needed for CI -> the package is not installed (but in the docker image this is not necessary)
    con.execute("INSTALL httpfs;") 
    try:
        con.execute(
            f"""
            COPY (
                SELECT ? AS action, ? AS value, NOW()::TIMESTAMP AS timestamp
            ) TO '{path}' (FORMAT PARQUET)
            """,
            [action, json.dumps(value)],
        )
    finally:
        con.close()
    return path


class TestCompactor:
    def test_noop_when_prefix_empty(self, moto_s3):
        result = compactor_handler({}, None)
        assert result["status"] == "noop"
        with pytest.raises(moto_s3.exceptions.ClientError):
            moto_s3.head_object(Bucket=BUCKET_NAME, Key=SNAPSHOT_KEY)

    def test_publishes_snapshot_with_cache_control(self, moto_s3, tmp_path):
        for i, (action, value) in enumerate([
            ("REGISTRATION", {"pseudo": "alice"}),
            ("REGISTRATION", {"pseudo": "bob"}),
            ("FLAG_SUBMISSION_SUCCESS", {"pseudo": "alice", "scenario": 1}),
        ]):
            local = _write_event_parquet(tmp_path, f"evt_{i}.parquet", action, value)
            moto_s3.upload_file(
                local,
                BUCKET_NAME,
                f"leaderboard/ctf-events/{action}_20260421T00000{i}_abcdef01.parquet",
            )

        result = compactor_handler({}, None)
        assert result["status"] == "ok"

        head = moto_s3.head_object(Bucket=BUCKET_NAME, Key=SNAPSHOT_KEY)
        assert head["CacheControl"] == SNAPSHOT_CACHE_CONTROL
        assert head["ContentType"] == "application/vnd.apache.parquet"

        snapshot_local = tmp_path / "snapshot.parquet"
        moto_s3.download_file(BUCKET_NAME, SNAPSHOT_KEY, str(snapshot_local))
        con = duckdb.connect()
        try:
            count = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)", [str(snapshot_local)]
            ).fetchone()[0]
        finally:
            con.close()
        assert count == 3

    def test_cleans_up_tmp_object(self, moto_s3, tmp_path):
        local = _write_event_parquet(tmp_path, "evt.parquet", "REGISTRATION", {"pseudo": "z"})
        moto_s3.upload_file(
            local,
            BUCKET_NAME,
            "leaderboard/ctf-events/REGISTRATION_20260421T000000_deadbeef.parquet",
        )

        compactor_handler({}, None)

        listing = moto_s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="leaderboard/snapshot.tmp.")
        assert listing.get("KeyCount", 0) == 0
