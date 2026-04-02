"""
Génère des fichiers Parquet de résultats fictifs pour le développement local.
Simule des soumissions validées comme si elles venaient du Lambda.

Usage :
    cd docs/dev-data
    python generate.py
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pyarrow as pa
import pyarrow.parquet as pq

RESULTS = [
    # (pseudo, scenario, minutes_after_start)
    ("alice",   1,  5),
    ("bob",     1, 12),
    ("charlie", 1, 18),
    ("alice",   2, 35),
    ("bob",     2, 50),
    ("alice",   3, 90),
    ("charlie", 2, 95),
    ("bob",     3, 110),
    ("alice",   4, 140),
    ("charlie", 3, 160),
    ("bob",     4, 200),
    ("charlie", 4, 250),
]

start = datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc)
output_dir = os.path.dirname(os.path.abspath(__file__))

schema = pa.schema([
    pa.field("pseudo",    pa.string()),
    pa.field("scenario",  pa.int32()),
    pa.field("solved_at", pa.string()),
])

pseudos, scenarios, solved_ats = [], [], []
for pseudo, scenario, minutes in RESULTS:
    pseudos.append(pseudo)
    scenarios.append(scenario)
    solved_ats.append((start + timedelta(minutes=minutes)).isoformat())

table = pa.table(
    {"pseudo": pseudos, "scenario": scenarios, "solved_at": solved_ats},
    schema=schema,
)
output_path = os.path.join(output_dir, "results.parquet")
pq.write_table(table, output_path)
print(f"{len(RESULTS)} résultats écrits dans {output_path}")

# ── Locations (scénario 3) ────────────────────────────────────────────────────

LOCATIONS = [
    # (person, role, lat, lon, city, note)
    ("Bibliothèque du Lac", "library", 48.8566,   2.3522,   "Paris",    "Point de départ — registres de prêts"),
    ("Quackie Chan",        "target",  48.879226, 2.283274, "Paris",    "Domicile réel — coordonnées dans addresses (is_current=true)"),
    ("Hugh Quackman",       "decoy",   44.837789, -0.579187,"Bordeaux", "Leurre — coordonnées du père dans addresses"),
]

loc_schema = pa.schema([
    pa.field("person", pa.string()),
    pa.field("role",   pa.string()),
    pa.field("lat",    pa.float64()),
    pa.field("lon",    pa.float64()),
    pa.field("city",   pa.string()),
    pa.field("note",   pa.string()),
])

loc_table = pa.table(
    {
        "person": [r[0] for r in LOCATIONS],
        "role":   [r[1] for r in LOCATIONS],
        "lat":    [r[2] for r in LOCATIONS],
        "lon":    [r[3] for r in LOCATIONS],
        "city":   [r[4] for r in LOCATIONS],
        "note":   [r[5] for r in LOCATIONS],
    },
    schema=loc_schema,
)
loc_path = os.path.join(output_dir, "locations.parquet")
pq.write_table(loc_table, loc_path)
print(f"{len(LOCATIONS)} localisations écrites dans {loc_path}")
