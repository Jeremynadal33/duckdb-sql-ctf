"""Scenario 5 — Generate a DuckDB file with persons + relationships tables for DuckPGQ."""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from faker import Faker

from data_generator.config import CTFConfig
from data_generator.constants import (
    FAKER_SEED,
    FIGURANT_NAMES,
    FLAG_SCENARIO5,
    QUACKIE_CHAN_EMPLOYEE_ID,
)

NUM_NOISE_PERSONS = 80
NUM_NOISE_RELATIONSHIPS = 200

RELATIONSHIP_TYPES = [
    "ami",
    "collègue",
    "voisin",
    "connaissance",
    "mentor",
    "ancien collègue",
    "camarade d'études",
]

FAMILY_TYPES = ["frère", "sœur", "parent", "enfant", "conjoint", "cousin"]

QUACKIE_SISTER_ID  = 43
HUGH_QUACKMAN_ID   = 44


def _build_key_persons() -> list[dict]:
    return [
        {
            "id": QUACKIE_CHAN_EMPLOYEE_ID,
            "first_name": "Quackie",
            "last_name": "Chan",
            "date_of_birth": date(1978, 9, 3).isoformat(),
            "occupation": "Médecin généraliste",
            "notes": "Décédé. Ancien employé de la Clinique du Lac.",
        },
        {
            "id": QUACKIE_SISTER_ID,
            "first_name": "Quackella",
            "last_name": "Chan",
            "date_of_birth": date(1982, 6, 21).isoformat(),
            "occupation": "Assistante vétérinaire",
            "notes": "",
        },
        {
            "id": HUGH_QUACKMAN_ID,
            "first_name": "Hugh",
            "last_name": "Quackman",
            "date_of_birth": date(1979, 11, 8).isoformat(),
            "occupation": "Taxidermiste",
            "notes": "Pere de famille, ex mari de Quackella. A un casier judiciaire pour etre un vrai papa poule.",
        },
    ]


def _build_noise_persons(fake: Faker) -> list[dict]:
    persons = []
    used_ids = {QUACKIE_CHAN_EMPLOYEE_ID, QUACKIE_SISTER_ID, HUGH_QUACKMAN_ID}
    for name in FIGURANT_NAMES:
        parts = name.split(" ", 1)
        pid = fake.unique.random_int(min=100, max=9999)
        while pid in used_ids:
            pid = fake.unique.random_int(min=100, max=9999)
        used_ids.add(pid)
        persons.append({
            "id": pid,
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else "",
            "date_of_birth": fake.date_of_birth(minimum_age=20, maximum_age=70).isoformat(),
            "occupation": fake.job(),
            "notes": "",
        })

    for _ in range(NUM_NOISE_PERSONS - len(FIGURANT_NAMES)):
        pid = fake.unique.random_int(min=100, max=9999)
        while pid in used_ids:
            pid = fake.unique.random_int(min=100, max=9999)
        used_ids.add(pid)
        persons.append({
            "id": pid,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "date_of_birth": fake.date_of_birth(minimum_age=20, maximum_age=70).isoformat(),
            "occupation": fake.job(),
            "notes": "",
        })

    return persons


def _build_relationships(fake: Faker, all_persons: list[dict]) -> list[dict]:
    relationships = []
    used_pairs: set[tuple[int, int]] = set()
    rel_id = 1

    # ── Key chain: Quackie → sœur → Quackella → conjoint → Hugh Quackman (flag here) ──
    relationships.append({
        "id": rel_id,
        "person_id_1": QUACKIE_CHAN_EMPLOYEE_ID,
        "person_id_2": QUACKIE_SISTER_ID,
        "relationship_type": "sœur",
        "notes": "",
    })
    used_pairs.add((QUACKIE_CHAN_EMPLOYEE_ID, QUACKIE_SISTER_ID))
    rel_id += 1

    relationships.append({
        "id": rel_id,
        "person_id_1": QUACKIE_SISTER_ID,
        "person_id_2": HUGH_QUACKMAN_ID,
        "relationship_type": "conjoint",
        "notes": FLAG_SCENARIO5,
    })
    used_pairs.add((QUACKIE_SISTER_ID, HUGH_QUACKMAN_ID))
    rel_id += 1

    # Quackie has a few noise connections (colleagues, friends) to make graph exploration interesting
    noise_ids = [p["id"] for p in all_persons if p["id"] not in (QUACKIE_CHAN_EMPLOYEE_ID, QUACKIE_SISTER_ID, HUGH_QUACKMAN_ID)]
    for pid in random.sample(noise_ids, min(6, len(noise_ids))):
        pair = (min(QUACKIE_CHAN_EMPLOYEE_ID, pid), max(QUACKIE_CHAN_EMPLOYEE_ID, pid))
        if pair not in used_pairs:
            relationships.append({
                "id": rel_id,
                "person_id_1": QUACKIE_CHAN_EMPLOYEE_ID,
                "person_id_2": pid,
                "relationship_type": fake.random_element(["collègue", "ami", "voisin"]),
                "notes": "",
            })
            used_pairs.add(pair)
            rel_id += 1

    # Noise relationships between random persons
    person_ids = [p["id"] for p in all_persons]
    attempts = 0
    while len(relationships) < NUM_NOISE_RELATIONSHIPS + len(relationships[:7]) and attempts < 5000:
        attempts += 1
        p1, p2 = random.sample(person_ids, 2)
        pair = (min(p1, p2), max(p1, p2))
        if pair in used_pairs:
            continue
        used_pairs.add(pair)
        rel_type = fake.random_element(RELATIONSHIP_TYPES + FAMILY_TYPES)
        relationships.append({
            "id": rel_id,
            "person_id_1": p1,
            "person_id_2": p2,
            "relationship_type": rel_type,
            "notes": "",
        })
        rel_id += 1

    return relationships


def generate_graph_db(output_dir: Path) -> Path:
    """Generate the network.duckdb file locally."""
    import duckdb

    fake = Faker("fr_FR")
    Faker.seed(FAKER_SEED)
    random.seed(FAKER_SEED)

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "network.duckdb"

    # Remove existing file for idempotency
    db_path.unlink(missing_ok=True)

    key_persons = _build_key_persons()
    noise_persons = _build_noise_persons(fake)
    all_persons = key_persons + noise_persons
    relationships = _build_relationships(fake, all_persons)

    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE persons (
            id            INTEGER PRIMARY KEY,
            first_name    VARCHAR NOT NULL,
            last_name     VARCHAR NOT NULL,
            date_of_birth DATE,
            occupation    VARCHAR,
            notes         VARCHAR DEFAULT ''
        )
    """)

    con.execute("""
        CREATE TABLE relationships (
            id                 INTEGER PRIMARY KEY,
            person_id_1        INTEGER NOT NULL REFERENCES persons(id),
            person_id_2        INTEGER NOT NULL REFERENCES persons(id),
            relationship_type  VARCHAR NOT NULL,
            notes              VARCHAR DEFAULT ''
        )
    """)

    con.executemany(
        "INSERT INTO persons VALUES (?, ?, ?, ?, ?, ?)",
        [(p["id"], p["first_name"], p["last_name"], p["date_of_birth"], p["occupation"], p["notes"])
         for p in all_persons],
    )

    con.executemany(
        "INSERT INTO relationships VALUES (?, ?, ?, ?, ?)",
        [(r["id"], r["person_id_1"], r["person_id_2"], r["relationship_type"], r["notes"])
         for r in relationships],
    )

    con.close()
    return db_path


def upload_to_s3(config: CTFConfig, output_dir: Path) -> None:
    """Upload the DuckDB file and graph JSON to S3."""
    import boto3

    s3 = boto3.client("s3")
    s3.upload_file(
        str(output_dir / "network.duckdb"),
        config.s3_bucket_name,
        "data/network.duckdb",
    )


def generate_graph(config: CTFConfig, output_dir: Path, upload: bool = True) -> Path:
    db_path = generate_graph_db(output_dir)
    if upload:
        upload_to_s3(config, output_dir)
    return db_path
