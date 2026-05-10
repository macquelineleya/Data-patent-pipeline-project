from pathlib import Path
import pandas as pd

RAW_DIR = Path(r"H:\patent_pipeline_project\data\raw\extracted")
CLEAN_DIR = Path(r"H:\patent_pipeline_project\data\cleaned")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

file_path = RAW_DIR / "g_inventor_disambiguated.tsv"

CHUNK_SIZE = 100_000
MAX_ROWS = None  # for testing first; later change to None for full file

def pick_column(columns, candidates):
    for col in candidates:
        if col in columns:
            return col
    return None

def append_csv(df, output_path):
    if df.empty:
        return
    write_header = not output_path.exists()
    df.to_csv(output_path, mode="a", header=write_header, index=False)

def main():
    header_df = pd.read_csv(file_path, sep="\t", nrows=0, low_memory=False)
    cols = list(header_df.columns)

    print("Available inventor columns:")
    print(cols)

    patent_col = pick_column(cols, ["patent_id"])
    inventor_col = pick_column(cols, ["inventor_id"])
    sequence_col = pick_column(cols, ["inventor_sequence"])
    first_name_col = pick_column(cols, ["disambig_inventor_name_first", "inventor_name_first"])
    last_name_col = pick_column(cols, ["disambig_inventor_name_last", "inventor_name_last"])
    gender_col = pick_column(cols, ["gender_code", "gender"])
    location_col = pick_column(cols, ["location_id"])

    needed_cols = [
        c for c in [
            patent_col,
            inventor_col,
            sequence_col,
            first_name_col,
            last_name_col,
            gender_col,
            location_col
        ] if c is not None
    ]

    inventors_out = CLEAN_DIR / "clean_inventors.csv"
    relationships_out = CLEAN_DIR / "clean_patent_inventor_relationships.csv"

    if inventors_out.exists():
        inventors_out.unlink()

    if relationships_out.exists():
        relationships_out.unlink()

    total_rows = 0

    for i, chunk in enumerate(
        pd.read_csv(
            file_path,
            sep="\t",
            usecols=needed_cols,
            chunksize=CHUNK_SIZE,
            low_memory=False
        ),
        start=1
    ):
        print(f"\nProcessing chunk {i} ...")

        if first_name_col and last_name_col:
            chunk["name"] = (
                chunk[first_name_col].fillna("").astype(str).str.strip() + " " +
                chunk[last_name_col].fillna("").astype(str).str.strip()
            ).str.strip()
        elif first_name_col:
            chunk["name"] = chunk[first_name_col].fillna("").astype(str).str.strip()
        elif last_name_col:
            chunk["name"] = chunk[last_name_col].fillna("").astype(str).str.strip()
        else:
            chunk["name"] = None

        inventor_keep = [c for c in [inventor_col, "name", gender_col, location_col] if c is not None]
        inventors_df = chunk[inventor_keep].copy()

        rename_map = {}
        if inventor_col:
            rename_map[inventor_col] = "inventor_id"
        if gender_col:
            rename_map[gender_col] = "gender"
        if location_col:
            rename_map[location_col] = "location_id"

        inventors_df = inventors_df.rename(columns=rename_map)
        inventors_df = inventors_df.drop_duplicates()

        rel_keep = [c for c in [patent_col, inventor_col, sequence_col, location_col] if c is not None]
        rel_df = chunk[rel_keep].copy()

        rel_rename = {}
        if patent_col:
            rel_rename[patent_col] = "patent_id"
        if inventor_col:
            rel_rename[inventor_col] = "inventor_id"
        if sequence_col:
            rel_rename[sequence_col] = "inventor_sequence"
        if location_col:
            rel_rename[location_col] = "location_id"

        rel_df = rel_df.rename(columns=rel_rename)
        rel_df = rel_df.drop_duplicates()

        append_csv(inventors_df, inventors_out)
        append_csv(rel_df, relationships_out)

        total_rows += len(chunk)
        print(f"Processed rows so far: {total_rows}")

        if MAX_ROWS is not None and total_rows >= MAX_ROWS:
            print("\nStopped at test limit.")
            break

    print("\nSaved clean_inventors.csv")
    print("Saved clean_patent_inventor_relationships.csv")
    print("Inventor cleaning completed.")

if __name__ == "__main__":
    main()