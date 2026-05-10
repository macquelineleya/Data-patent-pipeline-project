import sqlite3

conn = sqlite3.connect(r"H:\patent_pipeline_project\patents.db")

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
""").fetchall()

print("Tables in database:")
print(tables)

conn.close()