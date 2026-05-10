from pathlib import Path
import pandas as pd

print("Script has started...")

RAW_DIR = Path(r"H:\patent_pipeline_project\data\raw\extracted")

FILES = [
    "g_patent.tsv",
    "g_assignee_disambiguated.tsv",
    "g_location_disambiguated.tsv",
    "g_inventor_disambiguated.tsv",
    "g_patent_abstract.tsv" 
]

print(f"Looking inside: {RAW_DIR}")
print(f"Folder exists: {RAW_DIR.exists()}")

for file_name in FILES:
    file_path = RAW_DIR / file_name

    print("\n" + "=" * 80)
    print(f"FILE: {file_name}")
    print(f"Full path: {file_path}")
    print(f"Exists: {file_path.exists()}")
    print("=" * 80)

    if not file_path.exists():
        print("File not found. Check the filename and folder.")
        continue

    try:
        df = pd.read_csv(
            file_path,
            sep="\t",
            nrows=5,
            low_memory=False
        )

        print("\nCOLUMNS:")
        print(list(df.columns))

        print("\nFIRST 5 ROWS:")
        print(df.head())

    except Exception as e:
        print(f"Error reading {file_name}: {e}")

print("\nScript finished.")