"""Scenario 2 — Generate Parquet files (employees, badges, departments) and upload to S3."""

from __future__ import annotations

import json
import random
import string
from datetime import timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from faker import Faker

from data_generator.config import CTFConfig
from data_generator.constants import (
    BADGE_STATUSES,
    DEPARTMENTS,
    FAKER_SEED,
    QUACKIE_CHAN_BADGE_ID,
    QUACKIE_CHAN_EMPLOYEE_ID,
    TARGET_DATE,
)
from data_generator.models.parquet_models import Badge, Department, Employee

NUM_EMPLOYEES = 150

S3_README = """# Archives numériques — Bibliothèque du Lac

## Tables disponibles

- `employees/` — Annuaire du personnel (fichiers fragmentés)
- `badges/` — Registre des badges d'accès (fichiers fragmentés)
- `departments/` — Liste des départements (fichiers fragmentés)

Chaque dossier contient plusieurs fichiers `.parquet`.
"""


def _random_noise(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _build_employee_flag(config: CTFConfig) -> str:
    return f"FLAG{{pg_host={config.db_host},pg_port={config.db_port},pg_user={config.pg_ro_user}"


def _build_badge_flag(config: CTFConfig) -> str:
    return f",pg_password={config.pg_ro_password},pg_dbname={config.db_name}}}"


def _generate_departments() -> list[Department]:
    return [Department(**d) for d in DEPARTMENTS]


def _generate_employees(fake: Faker, config: CTFConfig) -> list[Employee]:
    employees: list[Employee] = []

    # Quackie Chan — target employee (the doctor, found dead)
    quackie_hire = TARGET_DATE.replace(year=TARGET_DATE.year - 8)
    employees.append(
        Employee(
            id=QUACKIE_CHAN_EMPLOYEE_ID,
            first_name="Quackie",
            last_name="Chan",
            department_id=1,  # Service Médical
            hire_date=quackie_hire,
            email="quackie.chan@bibliotheque-du-lac.fr",
            metadata=json.dumps({"info": _build_employee_flag(config)}),
        )
    )

    # Generate remaining employees
    used_ids = {QUACKIE_CHAN_EMPLOYEE_ID}
    for _ in range(NUM_EMPLOYEES - 1):
        emp_id = fake.unique.random_int(min=1, max=999)
        while emp_id in used_ids:
            emp_id = fake.unique.random_int(min=1, max=999)
        used_ids.add(emp_id)

        dept_id = fake.random_int(min=1, max=len(DEPARTMENTS))
        hire_date = fake.date_between(
            start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 16),
            end_date=TARGET_DATE.replace(year=TARGET_DATE.year - 1),
        )

        first_name = fake.first_name()
        last_name = fake.last_name()
        email = f"{first_name.lower()}.{last_name.lower()}@bibliotheque-du-lac.fr"

        employees.append(
            Employee(
                id=emp_id,
                first_name=first_name,
                last_name=last_name,
                department_id=dept_id,
                hire_date=hire_date,
                email=email,
                metadata=json.dumps({"info": _random_noise()}),
            )
        )

    return employees


def _generate_badges(
    fake: Faker, employees: list[Employee], config: CTFConfig
) -> list[Badge]:
    badges: list[Badge] = []

    for emp in employees:
        if emp.id == QUACKIE_CHAN_EMPLOYEE_ID:
            badges.append(
                Badge(
                    badge_id=QUACKIE_CHAN_BADGE_ID,
                    employee_id=emp.id,
                    issued_date=emp.hire_date + timedelta(days=14),
                    status="inactive",
                    metadata=json.dumps({"info": _build_badge_flag(config)}),
                )
            )
        else:
            badge_num = f"{emp.id:04d}"
            issued = emp.hire_date + timedelta(days=fake.random_int(min=1, max=30))
            status = fake.random_element(BADGE_STATUSES)
            badges.append(
                Badge(
                    badge_id=f"BADGE-{badge_num}",
                    employee_id=emp.id,
                    issued_date=issued,
                    status=status,
                    metadata=json.dumps({"info": _random_noise()}),
                )
            )

    return badges


def _write_parquet(data: list, schema: pa.Schema, path: Path) -> None:
    rows = [d.model_dump() for d in data]
    table = pa.table(
        {field.name: [r[field.name] for r in rows] for field in schema}, schema=schema
    )
    pq.write_table(table, path)


def _write_parquet_chunked(
    data: list,
    schema: pa.Schema,
    output_dir: Path,
    table_name: str,
    min_chunks: int,
    max_chunks: int,
) -> list[Path]:
    """Shuffle data and write to random-sized parquet chunks in a subdirectory."""
    shuffled = list(data)
    random.shuffle(shuffled)

    num_chunks = min(random.randint(min_chunks, max_chunks), len(shuffled))
    split_points = sorted(random.sample(range(1, len(shuffled)), num_chunks - 1))
    split_points = [0, *split_points, len(shuffled)]

    table_dir = output_dir / table_name
    table_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i in range(num_chunks):
        chunk = shuffled[split_points[i] : split_points[i + 1]]
        path = table_dir / f"part_{i + 1:03d}.parquet"
        _write_parquet(chunk, schema, path)
        paths.append(path)
    return paths


EMPLOYEE_SCHEMA = pa.schema(
    [
        pa.field("id", pa.int32()),
        pa.field("first_name", pa.string()),
        pa.field("last_name", pa.string()),
        pa.field("department_id", pa.int32()),
        pa.field("hire_date", pa.date32()),
        pa.field("email", pa.string()),
        pa.field("metadata", pa.string()),
    ]
)

BADGE_SCHEMA = pa.schema(
    [
        pa.field("badge_id", pa.string()),
        pa.field("employee_id", pa.int32()),
        pa.field("issued_date", pa.date32()),
        pa.field("status", pa.string()),
        pa.field("metadata", pa.string()),
    ]
)

DEPARTMENT_SCHEMA = pa.schema(
    [
        pa.field("dept_id", pa.int32()),
        pa.field("dept_name", pa.string()),
        pa.field("building", pa.string()),
        pa.field("floor", pa.int32()),
    ]
)


def generate_parquet(config: CTFConfig, output_dir: Path) -> Path:
    """Generate Parquet files locally."""
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    output_dir.mkdir(parents=True, exist_ok=True)

    departments = _generate_departments()
    employees = _generate_employees(fake, config)
    badges = _generate_badges(fake, employees, config)

    _write_parquet_chunked(
        departments, DEPARTMENT_SCHEMA, output_dir, "departments", min_chunks=2, max_chunks=3
    )
    _write_parquet_chunked(
        employees, EMPLOYEE_SCHEMA, output_dir, "employees", min_chunks=3, max_chunks=5
    )
    _write_parquet_chunked(
        badges, BADGE_SCHEMA, output_dir, "badges", min_chunks=3, max_chunks=5
    )

    # Write README for the bucket
    (output_dir / "README.md").write_text(S3_README, encoding="utf-8")

    return output_dir


def upload_to_s3(config: CTFConfig, output_dir: Path) -> None:
    """Upload generated Parquet files to S3."""
    import boto3

    s3 = boto3.client("s3")
    bucket = config.s3_bucket_name

    # Upload README
    s3.upload_file(str(output_dir / "README.md"), bucket, "data/README.md")

    # Upload chunked parquet subdirectories
    for table_name in ("employees", "badges", "departments"):
        table_dir = output_dir / table_name
        for parquet_file in sorted(table_dir.glob("*.parquet")):
            s3_key = f"data/{table_name}/{parquet_file.name}"
            s3.upload_file(str(parquet_file), bucket, s3_key)


def generate_and_upload_parquet(
    config: CTFConfig, output_dir: Path, upload: bool = True
) -> Path:
    """Generate Parquet files and optionally upload to S3."""
    path = generate_parquet(config, output_dir)
    if upload:
        upload_to_s3(config, output_dir)
    return path
