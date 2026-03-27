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
) -> None:
    """Scenario 1: Generate 500 JSON log files in a zip archive."""
    from data_generator.config import load_config
    from data_generator.generators.scenario1_logs import generate_logs

    config = load_config("../terraform")
    path = generate_logs(config, output_dir)
    typer.echo(f"Generated: {path}")


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
def postgres() -> None:
    """Scenario 3: Populate PostgreSQL tables."""
    from data_generator.config import load_config
    from data_generator.generators.scenario3_postgres import populate_postgres

    config = load_config()
    populate_postgres(config)
    typer.echo("PostgreSQL tables populated.")


@app.command(name="all")
def all_scenarios(
    output_dir: Path = typer.Option(Path("output"), help="Output directory"),
    upload: bool = typer.Option(True, help="Upload Parquet to S3"),
) -> None:
    """Run all scenarios in order."""
    from data_generator.config import load_config
    from data_generator.generators.scenario1_logs import generate_logs
    from data_generator.generators.scenario2_parquet import generate_and_upload_parquet
    from data_generator.generators.scenario3_postgres import populate_postgres

    config = load_config()

    typer.echo("Scenario 1: Generating library logs...")
    generate_logs(config, output_dir)

    typer.echo("Scenario 2: Generating Parquet files...")
    generate_and_upload_parquet(config, output_dir, upload)

    typer.echo("Scenario 3: Populating PostgreSQL...")
    populate_postgres(config)

    typer.echo("All scenarios generated.")
