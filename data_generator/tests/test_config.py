import json
from unittest.mock import MagicMock, patch


from data_generator.config import CTFConfig, load_config


class TestCTFConfig:
    def test_computed_fields(self):
        config = CTFConfig(
            db_endpoint="mydb.example.com:5432",
            db_name="ctfdb",
            pg_master_user="admin",
            pg_master_password="pass",
            pg_ro_user="reader",
            pg_ro_password="ro_pass",
            s3_bucket_name="bucket",
            iam_access_key_id="AKIA",
            iam_secret_access_key="secret",
        )
        assert config.db_host == "mydb.example.com"
        assert config.db_port == 5432

    def test_default_port(self):
        config = CTFConfig(
            db_endpoint="mydb.example.com",
            db_name="ctfdb",
            pg_master_user="admin",
            pg_master_password="pass",
            pg_ro_user="reader",
            pg_ro_password="ro_pass",
            s3_bucket_name="bucket",
            iam_access_key_id="AKIA",
            iam_secret_access_key="secret",
        )
        assert config.db_host == "mydb.example.com"
        assert config.db_port == 5432


class TestLoadConfig:
    def test_load_config_parses_terraform_outputs(self, tmp_path):
        tf_json = {
            "db_endpoint": {"value": "mydb.rds.amazonaws.com:5432"},
            "pg_user": {"value": "postgres"},
            "db_name": {"value": "ctfdb"},
            "pg_ro_user": {"value": "ctf_reader"},
            "s3_bucket_name": {"value": "duckdb-sql-ctf"},
            "iam_access_key_id": {"value": "AKIAEXAMPLE"},
            "ssm_pg_master_password": {"value": "/ctf/pg_master_password"},
            "ssm_pg_readonly_password": {"value": "/ctf/pg_readonly_password"},
        }

        def mock_run(args, **kwargs):
            from unittest.mock import MagicMock

            result = MagicMock()
            result.stdout = ""
            if args[1] == "output" and args[2] == "-json":
                result.stdout = json.dumps(tf_json)
            elif args[1] == "output" and args[2] == "-raw":
                name = args[3]
                if name == "iam_secret_access_key":
                    result.stdout = "iam_secret"
            return result

        def mock_get_parameter(Name, WithDecryption=False):
            ssm_values = {
                "/ctf/pg_master_password": "master_secret",
                "/ctf/pg_readonly_password": "ro_secret",
            }
            return {"Parameter": {"Value": ssm_values[Name]}}

        mock_ssm = MagicMock()
        mock_ssm.get_parameter = mock_get_parameter

        with (
            patch("data_generator.config.subprocess.run", side_effect=mock_run),
            patch("data_generator.config.boto3.client", return_value=mock_ssm),
        ):
            config = load_config(tmp_path)

        assert config.db_host == "mydb.rds.amazonaws.com"
        assert config.db_name == "ctfdb"
        assert config.pg_master_user == "postgres"
        assert config.pg_master_password == "master_secret"
        assert config.pg_ro_user == "ctf_reader"
        assert config.pg_ro_password == "ro_secret"
        assert config.iam_secret_access_key == "iam_secret"
        assert config.s3_bucket_name == "duckdb-sql-ctf"
