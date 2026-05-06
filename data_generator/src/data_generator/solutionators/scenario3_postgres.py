"""Scenario 3 solutionator — find Quackie Chan in PG, geocode address, read city info."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from data_generator.config import CTFConfig
from data_generator.solutionators._common import make_duckdb

FIND_PERSON_SQL = """
SELECT id FROM postgres_db.public.persons
WHERE first_name = '{first_name}' AND last_name = '{last_name}'
"""

FIND_CURRENT_ADDRESS_SQL = """
SELECT latitude, longitude FROM postgres_db.public.addresses
WHERE person_id = {person_id} AND is_current = TRUE
"""

REVERSE_GEOCODE_SQL = """
WITH req AS (
    SELECT http_get(
        'https://nominatim.openstreetmap.org/reverse',
        headers => MAP {{
            'User-Agent': 'DuckDB-CTF-Solutionator/1.0',
            'Accept': 'application/json'
        }},
        params => MAP {{
            'format': 'geocodejson',
            'lat': '{lat}',
            'lon': '{lon}',
            'layer': 'address'
        }}
    ) AS response
)
SELECT json_extract_string(response->>'body',
                           '$.features[0].properties.geocoding.city') AS city
FROM req
"""

FIND_CITY_INFO_SQL = """
SELECT metadata FROM postgres_db.public.city_information
WHERE city_name = '{city_name}'
"""


def solve_pg_geocode(
    con: duckdb.DuckDBPyConnection, first_name: str, last_name: str
) -> dict:
    """Run the find-person → address → reverse-geocode → city-info chain.

    Returns ``{"city": str, "metadata": dict}``. Shared between scenarios 3 and 6.
    """
    person = con.execute(
        FIND_PERSON_SQL.format(first_name=first_name, last_name=last_name)
    ).fetchone()
    if person is None:
        raise AssertionError(f"person {first_name} {last_name} not found in postgres_db")
    person_id = person[0]

    addr = con.execute(
        FIND_CURRENT_ADDRESS_SQL.format(person_id=person_id)
    ).fetchone()
    if addr is None:
        raise AssertionError(f"no current address for person_id={person_id}")
    lat, lon = addr

    city_row = con.execute(REVERSE_GEOCODE_SQL.format(lat=lat, lon=lon)).fetchone()
    city = city_row[0] if city_row else None
    if not city:
        raise AssertionError(f"reverse geocoding failed for ({lat}, {lon})")

    md_row = con.execute(FIND_CITY_INFO_SQL.format(city_name=city)).fetchone()
    if md_row is None:
        raise AssertionError(f"no city_information row for city_name={city!r}")
    metadata = json.loads(md_row[0]) if isinstance(md_row[0], str) else md_row[0]

    return {"city": city, "metadata": metadata}


def solve(
    config: CTFConfig,
    output_dir: Path,
    *,
    local: bool = False,
) -> str:
    """Run scenario 3's canonical solve and return the flag.

    Scenario 3 always reads from live PostgreSQL + live Nominatim — ``local``
    and ``output_dir`` are accepted for API symmetry but ignored.
    """
    from data_generator.generators.scenario3_postgres import build_scenario3_flag

    con = make_duckdb(
        config,
        extensions=("postgres",),
        community_extensions=("http_client",),
        pg=True,
    )
    try:
        result = solve_pg_geocode(con, "Quackie", "Chan")
    finally:
        con.close()

    flag = result["metadata"]["info"]
    expected = build_scenario3_flag()
    assert flag == expected, f"scenario 3 flag mismatch: got {flag!r}, expected {expected!r}"
    return flag
