"""Scenario 1 — Generate 500 JSON library log files and zip them."""

from __future__ import annotations

import json
import random
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

from data_generator.config import CTFConfig
from data_generator.constants import (
    DECOY_CITY,
    DOCUMENT_TYPE_WEIGHTS,
    FAKER_SEED,
    FIGURANT_NAMES,
    LIBRARY_BRANCH,
    NOISE_UNRETURNED_TYPES,
    NORMAL_NOTES,
    QUACKIE_VARIATIONS,
    TARGET_DATE,
)
from data_generator.models.json_models import LibraryLog, LogMetadata

NUM_FILES = 500
RECORDS_PER_FILE = 100
TOTAL_RECORDS = NUM_FILES * RECORDS_PER_FILE
NUM_SUSPECT_LOGS = 12
NUM_NOISE_UNRETURNED = 18
NUM_NORMAL_LOGS = TOTAL_RECORDS - NUM_SUSPECT_LOGS - NUM_NOISE_UNRETURNED

# Theft happens the day before TARGET_DATE (the CTF day)
_theft_date = TARGET_DATE - timedelta(days=1)
BASE_DATE = datetime(
    _theft_date.year, _theft_date.month, _theft_date.day, tzinfo=timezone.utc
)
# Baby birth date: ~8 months before the heist
_baby_birth_date = (TARGET_DATE - timedelta(days=240)).isoformat()


def build_flag(config: CTFConfig) -> str:
    return (
        f"FLAG{{aws_access_key_id={config.iam_access_key_id},"
        f"aws_secret_access_key={config.iam_secret_access_key},"
        f"bucket={config.s3_bucket_name}}}"
    )


def split_flag(flag: str, n: int = 12) -> list[str]:
    """Split flag into n roughly equal fragments."""
    chunk_size = len(flag) // n
    remainder = len(flag) % n
    fragments: list[str] = []
    offset = 0
    for i in range(n):
        size = chunk_size + (1 if i < remainder else 0)
        fragments.append(flag[offset : offset + size])
        offset += size
    return fragments


def _generate_checkout_time(fake: Faker) -> datetime:
    """Random time on 2024-11-15 between 08:00 and 17:00 UTC."""
    hour = fake.random_int(min=8, max=16)
    minute = fake.random_int(min=0, max=59)
    second = fake.random_int(min=0, max=59)
    return BASE_DATE.replace(hour=hour, minute=minute, second=second)


def _generate_suspect_logs(fake: Faker, flag_fragments: list[str]) -> list[LibraryLog]:
    """Generate the 12 suspect birth certificate logs with flag fragments."""
    # Generate 12 distinct checkout times sorted chronologically
    times: list[datetime] = []
    for i in range(NUM_SUSPECT_LOGS):
        # Spread across the day: 08:00 to 16:50, ~45 min apart
        hour = 8 + (i * 45) // 60
        minute = (i * 45) % 60
        second = fake.random_int(min=0, max=59)
        times.append(BASE_DATE.replace(hour=hour, minute=minute, second=second))
    times.sort()

    logs: list[LibraryLog] = []
    for i, (checkout_time, fragment) in enumerate(zip(times, flag_fragments)):
        name_variation = QUACKIE_VARIATIONS[i % len(QUACKIE_VARIATIONS)]
        baby_num = i + 1
        log = LibraryLog(
            log_id=fake.uuid4(),
            document_type="acte_de_naissance",
            document_title=(
                f"Acte de naissance — Lac de {DECOY_CITY} — "
                f"{_baby_birth_date} — Mère: Donna Duck — Bébé #{baby_num}"
            ),
            borrower_name=name_variation,
            timestamp_checkout=checkout_time,
            timestamp_return=None,
            metadata=LogMetadata(
                library_branch=LIBRARY_BRANCH,
                notes=fragment,
            ),
        )
        logs.append(log)
    return logs


def _generate_noise_unreturned_logs(fake: Faker) -> list[LibraryLog]:
    """Generate 18 unreturned logs as noise (not birth certificates by Quackie)."""
    logs: list[LibraryLog] = []
    for doc_type in NOISE_UNRETURNED_TYPES:
        checkout_time = _generate_checkout_time(fake)
        borrower = fake.random_element(FIGURANT_NAMES)
        log = LibraryLog(
            log_id=fake.uuid4(),
            document_type=doc_type,
            document_title=f"{doc_type.replace('_', ' ').title()} — {fake.city()} — {fake.date()}",
            borrower_name=borrower,
            timestamp_checkout=checkout_time,
            timestamp_return=None,
            metadata=LogMetadata(
                library_branch=LIBRARY_BRANCH,
                notes=fake.random_element(NORMAL_NOTES),
            ),
        )
        logs.append(log)
    return logs


def _generate_normal_logs(fake: Faker) -> list[LibraryLog]:
    """Generate the ~49,970 normal returned logs."""
    # Build weighted list of document types
    doc_types: list[str] = []
    for doc_type, count in DOCUMENT_TYPE_WEIGHTS.items():
        doc_types.extend([doc_type] * count)

    # Pad or trim to exactly NUM_NORMAL_LOGS
    random.shuffle(doc_types)
    if len(doc_types) < NUM_NORMAL_LOGS:
        extra = NUM_NORMAL_LOGS - len(doc_types)
        doc_types.extend(random.choices(list(DOCUMENT_TYPE_WEIGHTS.keys()), k=extra))
    doc_types = doc_types[:NUM_NORMAL_LOGS]

    logs: list[LibraryLog] = []
    for doc_type in doc_types:
        checkout_time = _generate_checkout_time(fake)
        hours_delta = fake.random_int(min=1, max=6)
        return_time = checkout_time + timedelta(hours=hours_delta)
        borrower = fake.random_element(FIGURANT_NAMES)

        log = LibraryLog(
            log_id=fake.uuid4(),
            document_type=doc_type,
            document_title=f"{doc_type.replace('_', ' ').title()} — {fake.city()} — {fake.date()}",
            borrower_name=borrower,
            timestamp_checkout=checkout_time,
            timestamp_return=return_time,
            metadata=LogMetadata(
                library_branch=LIBRARY_BRANCH,
                notes=fake.random_element(NORMAL_NOTES),
            ),
        )
        logs.append(log)
    return logs


def generate_logs(config: CTFConfig, output_dir: Path) -> Path:
    """Generate all library logs and write them to a zip file."""
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    output_dir.mkdir(parents=True, exist_ok=True)

    flag = build_flag(config)
    fragments = split_flag(flag)

    suspect_logs = _generate_suspect_logs(fake, fragments)
    noise_logs = _generate_noise_unreturned_logs(fake)
    normal_logs = _generate_normal_logs(fake)

    # Combine noise + normal logs and shuffle
    filler_logs = noise_logs + normal_logs
    random.shuffle(filler_logs)

    # Distribute into 500 files of 100 records each
    # Place each suspect in a distinct file, then fill with filler
    files: list[list[LibraryLog]] = [[] for _ in range(NUM_FILES)]

    # Assign each suspect to a different file
    suspect_file_indices = random.sample(range(NUM_FILES), NUM_SUSPECT_LOGS)
    for suspect, file_idx in zip(suspect_logs, suspect_file_indices):
        files[file_idx].append(suspect)

    # Fill remaining slots with filler logs
    filler_iter = iter(filler_logs)
    for file_logs in files:
        while len(file_logs) < RECORDS_PER_FILE:
            file_logs.append(next(filler_iter))

    # Shuffle records within each file so the suspect isn't always first
    for file_logs in files:
        random.shuffle(file_logs)

    # Write zip file
    zip_path = output_dir / "library_logs.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_logs in files:
            filename = f"log_{fake.uuid4()}.json"
            records = [log.model_dump(mode="json") for log in file_logs]
            zf.writestr(filename, json.dumps(records, ensure_ascii=False, indent=2))

    return zip_path


def upload_to_s3(config: CTFConfig, zip_path: Path) -> None:
    """Upload the library_logs.zip to S3 for public download."""
    import boto3

    s3 = boto3.client("s3")
    s3.upload_file(str(zip_path), config.s3_bucket_name, "data/library_logs.zip")
