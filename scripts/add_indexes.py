import sqlite3

conn = sqlite3.connect(r"H:\patent_pipeline_project\patents.db")
cur = conn.cursor()

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_pir_inventor_id ON patent_inventor_relationships(inventor_id);",
    "CREATE INDEX IF NOT EXISTS idx_pir_patent_id ON patent_inventor_relationships(patent_id);",
    "CREATE INDEX IF NOT EXISTS idx_pir_location_id ON patent_inventor_relationships(location_id);",
    "CREATE INDEX IF NOT EXISTS idx_pcr_company_id ON patent_company_relationships(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_pcr_patent_id ON patent_company_relationships(patent_id);",
    "CREATE INDEX IF NOT EXISTS idx_pcr_location_id ON patent_company_relationships(location_id);",
    "CREATE INDEX IF NOT EXISTS idx_inventors_inventor_id ON inventors(inventor_id);",
    "CREATE INDEX IF NOT EXISTS idx_companies_company_id ON companies(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_locations_location_id ON locations(location_id);",
    "CREATE INDEX IF NOT EXISTS idx_patents_year ON patents(year);"
]

for sql in indexes:
    cur.execute(sql)

conn.commit()
conn.close()

print("Indexes created successfully.")