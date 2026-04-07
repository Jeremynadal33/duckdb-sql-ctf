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

QUACKO_CHAN_ID = 43


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
            "id": QUACKO_CHAN_ID,
            "first_name": "Quacko",
            "last_name": "Chan",
            "date_of_birth": date(1980, 4, 15).isoformat(),
            "occupation": "Éleveur de canards",
            "notes": "Connu du service vétérinaire pour détention illégale d'animaux protégés.",
        },
    ]


def _build_noise_persons(fake: Faker) -> list[dict]:
    persons = []
    used_ids = {QUACKIE_CHAN_EMPLOYEE_ID, QUACKO_CHAN_ID}
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

    # ── Key relationship: Quacko is Quackie's brother — flag here ──
    relationships.append({
        "id": rel_id,
        "person_id_1": QUACKO_CHAN_ID,
        "person_id_2": QUACKIE_CHAN_EMPLOYEE_ID,
        "relationship_type": "frère",
        "notes": FLAG_SCENARIO5,
    })
    used_pairs.add((QUACKO_CHAN_ID, QUACKIE_CHAN_EMPLOYEE_ID))
    rel_id += 1

    # Quackie has a few noise connections (colleagues, friends) to make graph exploration interesting
    noise_ids = [p["id"] for p in all_persons if p["id"] not in (QUACKIE_CHAN_EMPLOYEE_ID, QUACKO_CHAN_ID)]
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


def _export_cytoscape_json(
    all_persons: list[dict], relationships: list[dict], output_dir: Path
) -> Path:
    """Export graph data as Cytoscape.js-compatible JSON for the web visualization."""
    import json

    nodes = [
        {
            "data": {
                "id": str(p["id"]),
                "label": f"{p['first_name']} {p['last_name']}",
                "occupation": p.get("occupation", ""),
                "notes": p.get("notes", ""),
                "key": p["id"] in (QUACKIE_CHAN_EMPLOYEE_ID, QUACKO_CHAN_ID),
                "isVictim": p["id"] == QUACKIE_CHAN_EMPLOYEE_ID,
                "isSuspect": p["id"] == QUACKO_CHAN_ID,
            }
        }
        for p in all_persons
    ]

    edges = [
        {
            "data": {
                "id": f"rel-{r['id']}",
                "source": str(r["person_id_1"]),
                "target": str(r["person_id_2"]),
                "label": r["relationship_type"],
                "notes": r["notes"],
                "isKeyEdge": bool(r["notes"]),
            }
        }
        for r in relationships
    ]

    graph_json = output_dir / "graph_data.json"
    graph_json.write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return graph_json


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

    # Export JSON for the web visualization (also copy to docs/graph/ for local dev)
    json_path = _export_cytoscape_json(all_persons, relationships, output_dir)
    docs_graph_dir = Path(__file__).resolve().parents[5] / "docs" / "graph"
    if docs_graph_dir.exists():
        import shutil
        shutil.copy2(json_path, docs_graph_dir / "data.json")

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
    s3.upload_file(
        str(output_dir / "graph_data.json"),
        config.s3_bucket_name,
        "data/graph_data.json",
    )


def generate_graph(config: CTFConfig, output_dir: Path, upload: bool = True) -> Path:
    db_path = generate_graph_db(output_dir)
    if upload:
        upload_to_s3(config, output_dir)
    return db_path
