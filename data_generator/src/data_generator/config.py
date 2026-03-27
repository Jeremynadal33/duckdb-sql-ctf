from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pydantic import BaseModel, computed_field


class CTFConfig(BaseModel):
    db_endpoint: str
    db_name: str
    pg_master_user: str
    pg_master_password: str
    pg_ro_user: str
    pg_ro_password: str
    s3_bucket_name: str
    iam_access_key_id: str
    iam_secret_access_key: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_host(self) -> str:
        return self.db_endpoint.split(":")[0]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def db_port(self) -> int:
        parts = self.db_endpoint.split(":")
        return int(parts[1]) if len(parts) > 1 else 5432


def _run_terraform(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["terraform", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _get_tf_output_json(terraform_dir: Path) -> dict:
    raw = _run_terraform(["output", "-json"], terraform_dir)
    return json.loads(raw)


def _get_tf_output_raw(name: str, terraform_dir: Path) -> str:
    return _run_terraform(["output", "-raw", name], terraform_dir)


def load_config(terraform_dir: Path | None = None) -> CTFConfig:
    """Load CTF configuration from terraform outputs."""
    if terraform_dir is None:
        terraform_dir = Path(__file__).resolve().parents[3] / "terraform"

    outputs = _get_tf_output_json(terraform_dir)

    # Sensitive outputs must be fetched individually with -raw
    pg_ro_password = _get_tf_output_raw("pg_ro_password", terraform_dir)
    iam_secret_access_key = _get_tf_output_raw("iam_secret_access_key", terraform_dir)

    return CTFConfig(
        db_endpoint=outputs["db_endpoint"]["value"],
        db_name=outputs["db_name"]["value"],
        pg_master_user=outputs["pg_user"]["value"],
        pg_master_password=outputs["pg_password"]["value"],
        pg_ro_user=outputs["pg_ro_user"]["value"],
        pg_ro_password=pg_ro_password,
        s3_bucket_name=outputs["s3_bucket_name"]["value"],
        iam_access_key_id=outputs["iam_access_key_id"]["value"],
        iam_secret_access_key=iam_secret_access_key,
    )
