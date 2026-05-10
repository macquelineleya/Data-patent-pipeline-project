from pathlib import Path
import sqlite3
import pandas as pd

PROJECT_DIR = Path(r"H:\patent_pipeline_project")
DB_PATH = PROJECT_DIR / "patents.db"

queries = {
    "top_inventors": """
        SELECT
            i.inventor_id,
            i.name,
            COUNT(DISTINCT pir.patent_id) AS patent_count
        FROM inventors i
        JOIN patent_inventor_relationships pir
            ON i.inventor_id = pir.inventor_id
        GROUP BY i.inventor_id, i.name
        ORDER BY patent_count DESC
        LIMIT 10;
    """,
    "top_companies": """
        SELECT
            c.company_id,
            c.name,
            COUNT(DISTINCT pcr.patent_id) AS patent_count
        FROM companies c
        JOIN patent_company_relationships pcr
            ON c.company_id = pcr.company_id
        GROUP BY c.company_id, c.name
        ORDER BY patent_count DESC
        LIMIT 10;
    """,
    "top_countries": """
        SELECT
            l.country,
            COUNT(DISTINCT pir.patent_id) AS patent_count
        FROM patent_inventor_relationships pir
        JOIN locations l
            ON pir.location_id = l.location_id
        WHERE l.country IS NOT NULL
        GROUP BY l.country
        ORDER BY patent_count DESC
        LIMIT 10;
    """,
    "yearly_trends": """
        SELECT
            year,
            COUNT(*) AS patent_count
        FROM patents
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year;
    """
}

def main():
    conn = sqlite3.connect(DB_PATH)

    try:
        for name, query in queries.items():
            print("\n" + "=" * 60)
            print(name.upper())
            print("=" * 60)

            df = pd.read_sql_query(query, conn)
            print(df.head(10))

    finally:
        conn.close()

if __name__ == "__main__":
    main()