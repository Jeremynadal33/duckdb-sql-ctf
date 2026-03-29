import duckdb

EXPECTED_SCHEMA = [
    ("pseudo", "VARCHAR"),
    ("scenario", "INTEGER"),
    ("flag", "VARCHAR"),
]


def validate_schema(parquet_path: str) -> bool:
    con = duckdb.connect()
    result = con.execute(
        "SELECT name, duckdb_type FROM parquet_schema(?) WHERE duckdb_type IS NOT NULL",
        [parquet_path],
    ).fetchall()
    con.close()
    return result == EXPECTED_SCHEMA


def extract_submission(parquet_path: str) -> tuple[str, int, str]:
    con = duckdb.connect()
    row = con.execute(
        "SELECT pseudo, scenario, flag FROM read_parquet(?)", [parquet_path]
    ).fetchone()
    con.close()
    if row is None:
        raise ValueError("Parquet file is empty")
    return (row[0], row[1], row[2])


def check_flag(submitted: str, expected: str) -> bool:
    return submitted.strip() == expected.strip()
