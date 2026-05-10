from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(r"H:\patent_pipeline_project")
RAW_DIR = PROJECT_DIR / "data" / "raw" / "extracted"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"

patents_path = CLEAN_DIR / "clean_patents.csv"
abstracts_path = RAW_DIR / "g_patent_abstract.tsv"

CHUNK_SIZE = 100_000

def pick_column(columns, candidates):
    for col in candidates:
        if col in columns:
            return col
    return None

def main():
    if not patents_path.exists():
        raise FileNotFoundError(f"Missing {patents_path}")

    if not abstracts_path.exists():
        raise FileNotFoundError(f"Missing {abstracts_path}")

    patents_df = pd.read_csv(patents_path, low_memory=False)
    print("Loaded clean_patents.csv")

    header_df = pd.read_csv(abstracts_path, sep="\t", nrows=0, low_memory=False)
    cols = list(header_df.columns)
    print("Abstract file columns:")
    print(cols)

    patent_col = pick_column(cols, ["patent_id"])
    abstract_col = pick_column(cols, ["patent_abstract", "abstract"])

    if not patent_col or not abstract_col:
        raise ValueError("Could not find patent_id and abstract column in g_patent_abstract.tsv")

    abstract_chunks = []
    total_rows = 0

    for i, chunk in enumerate(
        pd.read_csv(
            abstracts_path,
            sep="\t",
            usecols=[patent_col, abstract_col],
            chunksize=CHUNK_SIZE,
            low_memory=False
        ),
        start=1
    ):
        chunk = chunk.rename(columns={
            patent_col: "patent_id",
            abstract_col: "abstract"
        }).drop_duplicates(subset=["patent_id"])

        abstract_chunks.append(chunk)
        total_rows += len(chunk)
        print(f"Processed abstract chunk {i} | rows so far: {total_rows}")

    abstracts_df = pd.concat(abstract_chunks, ignore_index=True)
    abstracts_df = abstracts_df.drop_duplicates(subset=["patent_id"])

    merged_df = patents_df.merge(abstracts_df, on="patent_id", how="left")

    cols_order = ["patent_id", "title", "abstract", "filing_date", "year"]
    existing_cols = [c for c in cols_order if c in merged_df.columns]
    merged_df = merged_df[existing_cols]

    merged_df.to_csv(patents_path, index=False)
    print("\nUpdated clean_patents.csv with abstract column.")
    print(merged_df.head())

if __name__ == "__main__":
    main()