"""Generator entry points for the CTF data."""

from __future__ import annotations

from pathlib import Path

import typer

from data_generator.config import CTFConfig


def generate_all(config: CTFConfig, output_dir: Path, upload: bool = True) -> None:
    """Run every scenario generator in order. Optionally pushes to S3/RDS."""
    from data_generator.generators.scenario1_logs import generate_logs, upload_to_s3
    from data_generator.generators.scenario2_parquet import generate_and_upload_parquet
    from data_generator.generators.scenario3_postgres import populate_postgres
    from data_generator.generators.scenario4_iceberg import generate_iceberg
    from data_generator.generators.scenario5_graph import generate_graph

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
