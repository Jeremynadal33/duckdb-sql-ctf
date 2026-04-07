"""Scenario 4 — Generate an Iceberg badges table with time-travel snapshots."""

from __future__ import annotations

import json
import random
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
from faker import Faker
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import EqualTo

from data_generator.config import CTFConfig
from data_generator.constants import (
    BADGE_STATUSES,
    FAKER_SEED,
    FLAG_SCENARIO4_PLACEHOLDER,
    FLAG_SNAPSHOT_INDEX,
    NUM_ICEBERG_SNAPSHOTS,
    QUACKIE_CHAN_BADGE_ID,
    QUACKIE_CHAN_EMPLOYEE_ID,
    QUACKIE_DEATH_DATE,
    TARGET_DATE,
)
from data_generator.models.parquet_models import Badge, Employee

NUM_EMPLOYEES = 150

ICEBERG_SCHEMA = pa.schema(
    [
        pa.field("badge_id", pa.string()),
        pa.field("employee_id", pa.int32()),
        pa.field("issued_date", pa.date32()),
        pa.field("status", pa.string()),
        pa.field("metadata", pa.string()),
    ]
)

TABLE_NAMESPACE = "badges"
TABLE_NAME = "badges"


def _random_noise(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _badges_to_arrow(badges: list[Badge]) -> pa.Table:
    """Convert a list of Badge models to a PyArrow table."""
    return pa.table(
        {
            "badge_id": [b.badge_id for b in badges],
            "employee_id": [b.employee_id for b in badges],
            "issued_date": [b.issued_date for b in badges],
            "status": [b.status for b in badges],
            "metadata": [b.metadata for b in badges],
        },
        schema=ICEBERG_SCHEMA,
    )


def _generate_employees(fake: Faker) -> list[Employee]:
    """Generate a minimal employee list (only IDs and hire dates needed for badge generation)."""
    employees: list[Employee] = []
    quackie_hire = TARGET_DATE.replace(year=TARGET_DATE.year - 8)
    employees.append(
        Employee(
            id=QUACKIE_CHAN_EMPLOYEE_ID,
            first_name="Quackie",
            last_name="Chan",
            department_id=1,
            hire_date=quackie_hire,
            email="quackie.chan@bibliotheque-du-lac.fr",
            metadata="",
        )
    )
    used_ids = {QUACKIE_CHAN_EMPLOYEE_ID}
    for _ in range(NUM_EMPLOYEES - 1):
        emp_id = fake.unique.random_int(min=1, max=999)
        while emp_id in used_ids:
            emp_id = fake.unique.random_int(min=1, max=999)
        used_ids.add(emp_id)
        hire_date = fake.date_between(
            start_date=TARGET_DATE.replace(year=TARGET_DATE.year - 16),
            end_date=TARGET_DATE.replace(year=TARGET_DATE.year - 1),
        )
        employees.append(
            Employee(
                id=emp_id,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                department_id=fake.random_int(min=1, max=10),
                hire_date=hire_date,
                email="",
                metadata="",
            )
        )
    return employees


def _generate_initial_badges(fake: Faker, employees: list[Employee]) -> list[Badge]:
    """Generate the initial set of badges. Quackie is active with the real flag."""
    badges: list[Badge] = []
    for emp in employees:
        if emp.id == QUACKIE_CHAN_EMPLOYEE_ID:
            badges.append(
                Badge(
                    badge_id=QUACKIE_CHAN_BADGE_ID,
                    employee_id=emp.id,
                    issued_date=emp.hire_date + timedelta(days=14),
                    status="active",
                    metadata=json.dumps({"info": FLAG_SCENARIO4_PLACEHOLDER}),
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


def _make_quackie_badge_update(
    base_badges: list[Badge], snapshot_idx: int, total_snapshots: int
) -> Badge:
    """Build an updated Quackie badge for a given snapshot.

    - Snapshot at FLAG_SNAPSHOT_INDEX keeps the real flag.
    - Later snapshots (past the death date) mark the badge inactive.
    - All others get noise metadata.
    """
    quackie = next(b for b in base_badges if b.badge_id == QUACKIE_CHAN_BADGE_ID)

    if snapshot_idx == FLAG_SNAPSHOT_INDEX:
        # This is the flag snapshot — keep as-is from initial generation
        return quackie

    is_after_death = snapshot_idx > FLAG_SNAPSHOT_INDEX + 2
    return Badge(
        badge_id=quackie.badge_id,
        employee_id=quackie.employee_id,
        issued_date=quackie.issued_date,
        status="inactive" if is_after_death else "active",
        metadata=json.dumps({"info": _random_noise()}),
    )


def _compute_snapshot_timestamps(total_snapshots: int) -> list[int]:
    """Compute snapshot timestamps (ms since epoch) for all Iceberg snapshots.

    overwrite() creates 2 snapshots (delete + append), so for N logical updates
    we get 1 + (N-1)*2 actual snapshots. We assign timestamps based on logical
    grouping:
      - Snapshot 0 (initial append) = logical update 0
      - Snapshots 1-2 (delete+append) = logical update 1
      - Snapshots 3-4 (delete+append) = logical update 2 (FLAG if FLAG_SNAPSHOT_INDEX==2)
      - etc.

    All snapshots up to and including the FLAG logical update get pre-death timestamps.
    All snapshots after get post-death timestamps.
    """
    death_dt = datetime(
        QUACKIE_DEATH_DATE.year, QUACKIE_DEATH_DATE.month, QUACKIE_DEATH_DATE.day,
        tzinfo=timezone.utc,
    )

    # Map each actual snapshot index to its logical update index
    # Snapshot 0 → logical 0, snapshots 1-2 → logical 1, snapshots 3-4 → logical 2, etc.
    def logical_index(snap_idx: int) -> int:
        if snap_idx == 0:
            return 0
        return (snap_idx - 1) // 2 + 1

    timestamps: list[int] = []
    for i in range(total_snapshots):
        li = logical_index(i)
        if li <= FLAG_SNAPSHOT_INDEX:
            # Before death: space from 90 days before death
            offset = 90 - li * 20
            ts = death_dt - timedelta(days=offset)
        else:
            # After death: space from 2 days after, 3 days apart per logical step
            steps_after = li - FLAG_SNAPSHOT_INDEX - 1
            ts = death_dt + timedelta(days=2 + steps_after * 3)
        timestamps.append(int(ts.timestamp() * 1000))

    return timestamps


def _patch_metadata_timestamps(metadata_dir: Path) -> None:
    """Modify snapshot timestamps in the latest Iceberg metadata JSON file."""
    # Find the latest metadata file (highest version number, e.g. 00009-xxx.metadata.json)
    meta_files = sorted(metadata_dir.glob("*.metadata.json"))
    if not meta_files:
        return

    latest_meta = meta_files[-1]
    with open(latest_meta, "r") as f:
        metadata = json.load(f)

    snapshots = metadata.get("snapshots", [])
    # Sort snapshots by their sequence-number to ensure correct ordering
    snapshots.sort(key=lambda s: s.get("sequence-number", s.get("snapshot-id", 0)))

    target_timestamps = _compute_snapshot_timestamps(len(snapshots))

    for i, snapshot in enumerate(snapshots):
        snapshot["timestamp-ms"] = target_timestamps[i]

    # Update last-updated-ms to match the latest snapshot
    metadata["last-updated-ms"] = target_timestamps[-1]

    # Also update the snapshot-log timestamps
    for i, entry in enumerate(metadata.get("snapshot-log", [])):
        if i < len(target_timestamps):
            entry["timestamp-ms"] = target_timestamps[i]

    with open(latest_meta, "w") as f:
        json.dump(metadata, f, indent=2)


def generate_iceberg(config: CTFConfig, output_dir: Path, upload: bool = True) -> Path:
    """Generate an Iceberg badges table with multiple snapshots."""
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    table_dir = output_dir / "badges"
    table_dir.mkdir(parents=True, exist_ok=True)

    warehouse_path = output_dir / "iceberg_warehouse"
    warehouse_path.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(
        "default",
        **{
            "type": "sql",
            "uri": f"sqlite:///{warehouse_path!s}/catalog.db",
            "warehouse": f"file://{warehouse_path!s}",
        },
    )

    # Create namespace and table
    catalog.create_namespace_if_not_exists(TABLE_NAMESPACE)
    try:
        catalog.drop_table(f"{TABLE_NAMESPACE}.{TABLE_NAME}")
    except Exception:
        pass
    table = catalog.create_table(f"{TABLE_NAMESPACE}.{TABLE_NAME}", schema=ICEBERG_SCHEMA)

    # Generate initial badges
    employees = _generate_employees(fake)
    initial_badges = _generate_initial_badges(fake, employees)

    # Snapshot 0: write all badges
    table.append(_badges_to_arrow(initial_badges))

    # Snapshots 1 through N-1: update Quackie's badge metadata
    for snapshot_idx in range(1, NUM_ICEBERG_SNAPSHOTS):
        updated_quackie = _make_quackie_badge_update(
            initial_badges, snapshot_idx, NUM_ICEBERG_SNAPSHOTS
        )
        table.overwrite(
            _badges_to_arrow([updated_quackie]),
            overwrite_filter=EqualTo("badge_id", QUACKIE_CHAN_BADGE_ID),  # type: ignore[misc,call-arg,arg-type]
        )

    # Patch snapshot timestamps in metadata
    iceberg_table_dir = warehouse_path / TABLE_NAMESPACE / TABLE_NAME
    metadata_dir = iceberg_table_dir / "metadata"
    _patch_metadata_timestamps(metadata_dir)

    if upload:
        _upload_to_s3(config, iceberg_table_dir)

    return iceberg_table_dir


def _upload_to_s3(config: CTFConfig, iceberg_table_dir: Path) -> None:
    """Upload the Iceberg table directory to S3."""
    import boto3

    s3 = boto3.client("s3")
    bucket = config.s3_bucket_name

    for file_path in iceberg_table_dir.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(iceberg_table_dir)
            s3_key = f"data/badges/{relative}"
            s3.upload_file(str(file_path), bucket, s3_key)
