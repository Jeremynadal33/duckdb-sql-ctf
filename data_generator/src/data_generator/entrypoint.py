"""CLI entrypoint for the CTF data generator."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(name="ctf-generate", help="Generate data for DuckDB SQL CTF")


@app.command()
def logs(
    output_dir: Path = typer.Option(
        Path("output"), help="Output directory for zip file"
    ),
    upload: bool = typer.Option(True, help="Upload zip to S3 after generation"),
) -> None:
    """Scenario 1: Generate 500 JSON log files in a zip archive."""
    from data_generator.config import load_config
    from data_generator.generators.scenario1_logs import generate_logs, upload_to_s3

    config = load_config()
    path = generate_logs(config, output_dir)
    typer.echo(f"Generated: {path}")
    if upload:
        upload_to_s3(config, path)
        typer.echo("Uploaded to S3.")


@app.command()
def parquet(
    output_dir: Path = typer.Option(
        Path("output"), help="Local output directory for parquet files"
    ),
    upload: bool = typer.Option(True, help="Upload to S3 after generation"),
) -> None:
    """Scenario 2: Generate Parquet files and optionally upload to S3."""
    from data_generator.config import load_config
    from data_generator.generators.scenario2_parquet import generate_and_upload_parquet

    config = load_config()
    generate_and_upload_parquet(config, output_dir, upload)
    typer.echo(f"Parquet files generated in: {output_dir}")
    if upload:
        typer.echo("Uploaded to S3.")


@app.command()
def iceberg(
    output_dir: Path = typer.Option(
        Path("output"), help="Local output directory for Iceberg table"
    ),
    upload: bool = typer.Option(True, help="Upload to S3 after generation"),
) -> None:
    """Scenario 4: Generate Iceberg badges table with time-travel snapshots."""
    from data_generator.config import load_config
    from data_generator.generators.scenario4_iceberg import generate_iceberg

    config = load_config()
    table_path = generate_iceberg(config, output_dir, upload=upload)
    typer.echo(f"Iceberg table: {table_path}")
    if upload:
        typer.echo("Uploaded to S3.")


@app.command()
def graph(
    output_dir: Path = typer.Option(
        Path("output"), help="Local output directory for the DuckDB file"
    ),
    upload: bool = typer.Option(True, help="Upload to S3 after generation"),
) -> None:
    """Scenario 5: Generate network.duckdb (persons + relationships for DuckPGQ)."""
    from data_generator.config import load_config
    from data_generator.generators.scenario5_graph import generate_graph

    config = load_config()
    db_path = generate_graph(config, output_dir, upload=upload)
    typer.echo(f"DuckDB file: {db_path}")
    if upload:
        typer.echo("Uploaded to S3.")


@app.command()
def locations(
    output: Path = typer.Option(
        Path(__file__).resolve().parents[3] / "docs" / "map" / "locations.js",
        help="Chemin du fichier JS généré",
    ),
) -> None:
    """Génère docs/map/locations.js depuis les constantes Python."""
    from data_generator.constants import (
        ARCHIVES_CITY, ARCHIVES_LAT, ARCHIVES_LON,
        CITY_HALL_CITY, CITY_HALL_LAT, CITY_HALL_LON,
        LIBRARY_CITY, LIBRARY_LAT, LIBRARY_LON,
        QUACKIE_CITY, QUACKIE_LAT, QUACKIE_LON,
        TARGET_CITY, TARGET_LAT, TARGET_LON,
    )

    content = f"""// AUTO-GENERATED — do not edit manually.
// Run: mise run generate:locations
// Source: data_generator/src/data_generator/constants.py

const LOCATION_COORDS = {{
  library:   {{ lat: {LIBRARY_LAT}, lon: {LIBRARY_LON}, city: '{LIBRARY_CITY}' }},
  archives:  {{ lat: {ARCHIVES_LAT}, lon: {ARCHIVES_LON}, city: '{ARCHIVES_CITY}' }},
  city_hall: {{ lat: {CITY_HALL_LAT}, lon: {CITY_HALL_LON}, city: '{CITY_HALL_CITY}' }},
  quackie:   {{ lat: {QUACKIE_LAT}, lon: {QUACKIE_LON}, city: '{QUACKIE_CITY}' }},
  target:    {{ lat: {TARGET_LAT}, lon: {TARGET_LON}, city: '{TARGET_CITY}' }},
}};
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    typer.echo(f"Generated: {output}")


@app.command()
def postgres(
    upload: bool = typer.Option(True, help="Upload answer file to S3"),
) -> None:
    """Scenario 3: Populate PostgreSQL tables."""
    from data_generator.config import load_config
    from data_generator.generators.scenario3_postgres import populate_postgres

    config = load_config()
    populate_postgres(config, upload=upload)
    typer.echo("PostgreSQL tables populated.")


@app.command(name="solve-all")
def solve_all(
    output_dir: Path = typer.Option(Path("output"), help="Working directory"),
    regenerate: bool = typer.Option(False, "--regenerate", help="Regenerate all data once before solving"),
    upload: bool = typer.Option(False, "--upload", help="Upload after regenerating"),
) -> None:
    """Run every solutionator end-to-end and verify each scenario's flag.

    Mirrors the player flow: scenario 1 reveals AWS credentials (used by 2/4/5),
    scenario 2 reveals PostgreSQL credentials (used by 3/6). Each flag is parsed
    and used to override the running config before the next scenario runs.

    With ``--regenerate``, every scenario's data is regenerated once up front
    (via generators.generate_all) and the solvers then read locally from
    output_dir.
    """
    from data_generator.config import load_config
    from data_generator.generators import generate_all
    from data_generator.solutionators import (
        scenario1_logs, scenario2_parquet, scenario3_postgres,
        scenario4_iceberg, scenario5_graph, scenario6_geocode,
    )
    from data_generator.solutionators._common import parse_kv_flag

    config = load_config()
    if regenerate:
        generate_all(config, output_dir, upload=upload)
    common = dict(output_dir=output_dir, local=regenerate)

    flag1 = scenario1_logs.solve(config=config, **common)
    typer.echo(f"[scenario 1] Flag: {flag1}")
    aws = parse_kv_flag(flag1)
    config = config.model_copy(update={
        "iam_access_key_id": aws["aws_access_key_id"],
        "iam_secret_access_key": aws["aws_secret_access_key"],
        "s3_bucket_name": aws["bucket"],
    })
    typer.echo(f"  → unlocked S3 access: bucket={aws['bucket']} key_id={aws['aws_access_key_id'][:10]}…")

    flag2 = scenario2_parquet.solve(config=config, **common)
    typer.echo(f"[scenario 2] Flag: {flag2}")
    pg = parse_kv_flag(flag2)
    config = config.model_copy(update={
        "db_endpoint": f"{pg['pg_host']}:{pg['pg_port']}",
        "db_name": pg["pg_dbname"],
        "pg_ro_user": pg["pg_user"],
        "pg_ro_password": pg["pg_password"],
    })
    typer.echo(f"  → unlocked PostgreSQL: host={pg['pg_host']} db={pg['pg_dbname']} user={pg['pg_user']}")

    for name, fn in [
        ("scenario 3", scenario3_postgres.solve),
        ("scenario 4", scenario4_iceberg.solve),
        ("scenario 5", scenario5_graph.solve),
        ("scenario 6", scenario6_geocode.solve),
    ]:
        flag = fn(config=config, **common)
        typer.echo(f"[{name}] Flag: {flag}")


@app.command(name="generate-all")
def generate_all_command(
    output_dir: Path = typer.Option(Path("output"), help="Output directory"),
    upload: bool = typer.Option(True, help="Upload Parquet to S3"),
) -> None:
    """Generate every scenario's data in order (mirror of solve-all)."""
    from data_generator.config import load_config
    from data_generator.generators import generate_all

    generate_all(load_config(), output_dir, upload=upload)
