"""Scenario 0 — Tutorial. Generate a public CSV of buildings and upload to S3.

The puzzle: among ~40 buildings, exactly one is a `bibliothèque` whose `message`
column holds the flag. Participants read the public CSV, filter on the type, and
read the message — practising the read → find → submit loop with no credentials.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from faker import Faker

from data_generator.config import CTFConfig
from data_generator.constants import FAKER_SEED, SCENARIO0_FLAG
from data_generator.models.csv_models import Building

NUM_BUILDINGS = 12
S3_KEY = "data/buildings.csv"

# Décoys : tout sauf "bibliothèque".
DECOY_TYPES = [
    "mairie",
    "école",
    "hôpital",
    "commissariat",
    "gymnase",
    "théâtre",
    "musée",
    "commerce",
    "gare",
    "pharmacie",
]


def build_flag() -> str:
    """The scenario 0 flag (kept in sync with terraform/locals.tf flag_scenario0)."""
    return SCENARIO0_FLAG


def _generate_buildings(fake: Faker) -> list[Building]:
    buildings: list[Building] = []

    # La bibliothèque — seule ligne porteuse du flag.
    buildings.append(
        Building(
            id=1,
            nom="Bibliothèque du Lac",
            type="bibliothèque",
            message=build_flag(),
        )
    )

    for i in range(2, NUM_BUILDINGS + 1):
        building_type = random.choice(DECOY_TYPES)
        buildings.append(
            Building(
                id=i,
                nom=f"{building_type.capitalize()} {fake.last_name()}",
                type=building_type,
                message="",
            )
        )

    random.shuffle(buildings)
    return buildings


def generate_csv(config: CTFConfig, output_dir: Path) -> Path:
    """Generate buildings.csv locally."""
    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    output_dir.mkdir(parents=True, exist_ok=True)
    buildings = _generate_buildings(fake)

    path = output_dir / "buildings.csv"
    fields = list(Building.model_fields.keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for building in buildings:
            writer.writerow(building.model_dump())

    return path


def upload_to_s3(config: CTFConfig, csv_path: Path) -> None:
    """Upload buildings.csv to S3 (public-read via the bucket policy)."""
    import boto3

    s3 = boto3.client("s3")
    s3.upload_file(str(csv_path), config.s3_bucket_name, S3_KEY)
