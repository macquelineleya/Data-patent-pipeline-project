from pathlib import Path
import sqlite3
import pandas as pd

PROJECT_DIR = Path(r"H:\patent_pipeline_project")
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
SQL_DIR = PROJECT_DIR / "sql"
DB_PATH = PROJECT_DIR / "patents.db"
SCHEMA_PATH = SQL_DIR / "schema.sql"

CHUNK_SIZE = 100_000

TABLE_CONFIG = [
    {"csv": "clean_patents.csv", "table": "patents", "columns": ["patent_id", "title","abstract", "filing_date", "year"]},
    {"csv": "clean_inventors.csv", "table": "inventors", "columns": ["inventor_id", "name", "gender", "location_id"]},
    {"csv": "clean_companies.csv", "table": "companies", "columns": ["company_id", "name"]},
    {"csv": "clean_locations.csv", "table": "locations", "columns": ["location_id", "country", "state", "city"]},
    {"csv": "clean_patent_company_relationships.csv", "table": "patent_company_relationships", "columns": ["patent_id", "company_id", "location_id"]},
    {"csv": "clean_patent_inventor_relationships.csv", "table": "patent_inventor_relationships", "columns": ["patent_id", "inventor_id", "inventor_sequence", "location_id"]},
]

def run_schema(conn):
    print(f"Looking for schema at: {SCHEMA_PATH}")
    print(f"Schema exists: {SCHEMA_PATH.exists()}")

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print("Running schema.sql ...")
    conn.executescript(schema_sql)
    conn.commit()
    print("Schema created successfully.")

def insert_chunk(conn, table_name, columns, df):
    use_cols = [c for c in columns if c in df.columns]
    df = df[use_cols].copy()
    df = df.where(pd.notna(df), None)

    placeholders = ", ".join(["?"] * len(use_cols))
    col_names = ", ".join(use_cols)

    sql = f"INSERT OR IGNORE INTO {table_name} ({col_names}) VALUES ({placeholders})"
    data = [tuple(row) for row in df.itertuples(index=False, name=None)]

    conn.executemany(sql, data)
    conn.commit()

def load_csv_in_chunks(conn, csv_name, table_name, columns):
    csv_path = CLEAN_DIR / csv_name
    print(f"\nChecking file: {csv_path}")
    print(f"Exists: {csv_path.exists()}")

    if not csv_path.exists():
        print(f"Skipping {csv_name} - file not found.")
        return

    total_rows = 0
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False), start=1):
        insert_chunk(conn, table_name, columns, chunk)
        total_rows += len(chunk)
        print(f"{table_name}: chunk {i} loaded, rows processed so far: {total_rows}")

    print(f"Finished loading {csv_name} into {table_name}.")

def print_table_counts(conn):
    print("\n================ DATABASE COUNTS ================")
    tables = [
        "patents",
        "inventors",
        "companies",
        "locations",
        "patent_company_relationships",
        "patent_inventor_relationships",
    ]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count}")

def main():
    print("Starting SQLite load process...")
    print(f"Database path: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        run_schema(conn)

        for config in TABLE_CONFIG:
            load_csv_in_chunks(conn, config["csv"], config["table"], config["columns"])

        print_table_counts(conn)
        print(f"\nDatabase created successfully at: {DB_PATH}")

    except Exception as e:
        print(f"\nERROR: {e}")
        raise

    finally:
        conn.close()
        print("\nSQLite connection closed.")

if __name__ == "__main__":
    main()