import pytest

from data_generator.config import CTFConfig


@pytest.fixture
def fake_config() -> CTFConfig:
    """CTFConfig with fake values — no terraform call needed."""
    return CTFConfig(
        db_endpoint="localhost:5432",
        db_name="ctfdb",
        pg_master_user="admin",
        pg_master_password="admin_pass",
        pg_ro_user="ctf_reader",
        pg_ro_password="readonly123",
        s3_bucket_name="duckdb-sql-ctf",
        iam_access_key_id="AKIAIOSFODNN7EXAMPLE",
        iam_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    )
