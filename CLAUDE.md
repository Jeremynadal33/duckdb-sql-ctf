# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CTF (Capture The Flag) project introducing DuckDB by learning to query multiple database engines. The infrastructure provisions a PostgreSQL 16 RDS instance on AWS that serves as one of the query targets.

## Terraform Commands

All Terraform commands run from the `terraform/` directory. Environment variables are loaded from the root `.env` file.

```bash
# Load env vars (AWS creds + PG credentials) before any terraform command
source .env

# Initialize (required after backend/provider changes)
terraform init

# Format, validate, plan, apply
terraform fmt
terraform validate
terraform plan
terraform apply

# Connect to the database locally
psql "host=$(terraform output -raw db_endpoint | cut -d: -f1) port=5432 dbname=$(terraform output -raw db_name) user=$TF_VAR_pg_user password=$TF_VAR_pg_password"
```

## Architecture

- **Infrastructure**: Terraform on AWS (eu-west-1), state stored in S3 (`s3://ippon-data-dev-tfstates-bucket/duckdb-sql-ctf/`)
- **Database**: PostgreSQL 16 on RDS (`db.t4g.micro`), publicly accessible on port 5432, inside a custom VPC with two public subnets
- **Terraform layout**: `provider.tf` (backend + provider + default tags), `network.tf` (VPC/subnets/IGW/routes), `security.tf` (SG), `database.tf` (RDS), `variables.tf`, `outputs.tf`
- **Credentials**: `pg_user` and `pg_password` are passed via `TF_VAR_*` env vars from `.env`

## Flag Logic (dual maintenance required!)

Flag construction logic lives in **two places that must stay in sync**:

1. **Python generators** (`data_generator/src/data_generator/generators/`) — build flags and embed them in generated data (JSON logs, Parquet metadata, Postgres rows)
2. **Terraform answer files** (`terraform/locals.tf` flags + `terraform/storage.tf` S3 objects) — upload expected flags to `s3://bucket/leaderboard/answers/scenario_{N}.txt` for the Lambda answer checker

When modifying flag format or content for any scenario, **update both places** or the answer checker will reject correct submissions.
