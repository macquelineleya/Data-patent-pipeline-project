from pathlib import Path
import pandas as pd

RAW_DIR = Path(r"H:\patent_pipeline_project\data\raw\extracted")
CLEAN_DIR = Path(r"H:\patent_pipeline_project\data\cleaned")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

FILES_AND_COLUMNS = {
    "g_patent.tsv": [
        "patent_id",
        "patent_title",
        "patent_date"
    ],
    "g_assignee_disambiguated.tsv": [
        "patent_id",
        "assignee_id",
        "disambig_assignee_organization",
        "location_id"
    ],
    "g_location_disambiguated.tsv": [
        "location_id",
        "disambig_country",
        "disambig_state",
        "disambig_city"
    ]
}

def available_columns(file_path, wanted_columns):
    header_df = pd.read_csv(file_path, sep="\t", nrows=0, low_memory=False)
    return [col for col in wanted_columns if col in header_df.columns]

def clean_patents():
    file_path = RAW_DIR / "g_patent.tsv"
    cols = available_columns(file_path, FILES_AND_COLUMNS["g_patent.tsv"])
    df = pd.read_csv(file_path, sep="\t", usecols=cols, low_memory=False)

    df = df.rename(columns={
        "patent_title": "title",
        "patent_date": "filing_date"
    })

    if "filing_date" in df.columns:
        df["year"] = pd.to_datetime(df["filing_date"], errors="coerce").dt.year

    df = df.drop_duplicates(subset=["patent_id"])
    df.to_csv(CLEAN_DIR / "clean_patents.csv", index=False)

    print("Saved clean_patents.csv")
    print(df.head())

def clean_companies():
    file_path = RAW_DIR / "g_assignee_disambiguated.tsv"
    cols = available_columns(file_path, FILES_AND_COLUMNS["g_assignee_disambiguated.tsv"])
    df = pd.read_csv(file_path, sep="\t", usecols=cols, low_memory=False)

    df = df.rename(columns={
        "assignee_id": "company_id",
        "disambig_assignee_organization": "name"
    })

    companies_df = df[["company_id", "name"]].dropna().drop_duplicates()
    companies_df.to_csv(CLEAN_DIR / "clean_companies.csv", index=False)

    relationships_df = df[["patent_id", "company_id", "location_id"]].dropna().drop_duplicates()
    relationships_df.to_csv(CLEAN_DIR / "clean_patent_company_relationships.csv", index=False)

    print("Saved clean_companies.csv")
    print(companies_df.head())

    print("Saved clean_patent_company_relationships.csv")
    print(relationships_df.head())

def clean_locations():
    file_path = RAW_DIR / "g_location_disambiguated.tsv"
    cols = available_columns(file_path, FILES_AND_COLUMNS["g_location_disambiguated.tsv"])
    df = pd.read_csv(file_path, sep="\t", usecols=cols, low_memory=False)

    df = df.rename(columns={
        "disambig_country": "country",
        "disambig_state": "state",
        "disambig_city": "city"
    })

    df = df.drop_duplicates(subset=["location_id"])
    df.to_csv(CLEAN_DIR / "clean_locations.csv", index=False)

    print("Saved clean_locations.csv")
    print(df.head())

def main():
    clean_patents()
    clean_companies()
    clean_locations()
    print("\nCore cleaning completed.")

if __name__ == "__main__":
    main()