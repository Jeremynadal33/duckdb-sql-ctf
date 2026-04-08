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
    dev: bool = typer.Option(False, "--dev", help="Utiliser une config locale sans Terraform"),
) -> None:
    """Scenario 1: Generate 500 JSON log files in a zip archive."""
    from data_generator.config import dev_config, load_config
    from data_generator.generators.scenario1_logs import generate_logs, upload_to_s3

    config = dev_config() if dev else load_config()
    path = generate_logs(config, output_dir)
    typer.echo(f"Generated: {path}")
    if upload and not dev:
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
    dev: bool = typer.Option(False, "--dev", help="Utiliser une config locale sans Terraform"),
) -> None:
    """Scenario 4: Generate Iceberg badges table with time-travel snapshots."""
    from data_generator.config import dev_config, load_config
    from data_generator.generators.scenario4_iceberg import generate_iceberg

    config = dev_config() if dev else load_config()
    table_path = generate_iceberg(config, output_dir, upload=upload and not dev)
    typer.echo(f"Iceberg table: {table_path}")
    if upload and not dev:
        typer.echo("Uploaded to S3.")


@app.command()
def graph(
    output_dir: Path = typer.Option(
        Path("output"), help="Local output directory for the DuckDB file"
    ),
    upload: bool = typer.Option(True, help="Upload to S3 after generation"),
    dev: bool = typer.Option(False, "--dev", help="Utiliser une config locale sans Terraform"),
) -> None:
    """Scenario 5: Generate network.duckdb (persons + relationships for DuckPGQ)."""
    from data_generator.config import dev_config, load_config
    from data_generator.generators.scenario5_graph import generate_graph

    config = dev_config() if dev else load_config()
    db_path = generate_graph(config, output_dir, upload=upload and not dev)
    typer.echo(f"DuckDB file: {db_path}")
    if upload and not dev:
        typer.echo("Uploaded to S3.")


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


@app.command(name="all")
def all_scenarios(
    output_dir: Path = typer.Option(Path("output"), help="Output directory"),
    upload: bool = typer.Option(True, help="Upload Parquet to S3"),
) -> None:
    """Run all scenarios in order."""
    from data_generator.config import load_config
    from data_generator.generators.scenario1_logs import generate_logs, upload_to_s3
    from data_generator.generators.scenario2_parquet import generate_and_upload_parquet
    from data_generator.generators.scenario3_postgres import populate_postgres
    from data_generator.generators.scenario4_iceberg import generate_iceberg
    from data_generator.generators.scenario5_graph import generate_graph

    config = load_config()

    typer.echo("Scenario 1: Generating library logs...")
    zip_path = generate_logs(config, output_dir)
    if upload:
        upload_to_s3(config, zip_path)

    typer.echo("Scenario 2: Generating Parquet files...")
    generate_and_upload_parquet(config, output_dir, upload)

    typer.echo("Scenario 3: Populating PostgreSQL...")
    populate_postgres(config, upload=upload)

    typer.echo("Scenario 4: Generating Iceberg badges table...")
    generate_iceberg(config, output_dir, upload=upload)

    typer.echo("Scenario 5: Generating network.duckdb...")
    generate_graph(config, output_dir, upload=upload)

    typer.echo("All scenarios generated.")
