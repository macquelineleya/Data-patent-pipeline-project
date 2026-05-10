from pathlib import Path
import requests
import time

PROJECT_DIR = Path(r"H:\patent_pipeline_project")
RAW_DIR = PROJECT_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "g_patent_abstract.tsv.zip": "https://zenodo.org/records/15783125/files/g_patent_abstract.tsv.zip?download=1"
}

CHUNK_SIZE = 1024 * 1024
MAX_RETRIES = 10

def download_with_resume(url: str, output_path: Path):
    temp_path = output_path.with_suffix(output_path.suffix + ".part")

    for attempt in range(1, MAX_RETRIES + 1):
        downloaded_bytes = temp_path.stat().st_size if temp_path.exists() else 0
        headers = {}

        if downloaded_bytes > 0:
            headers["Range"] = f"bytes={downloaded_bytes}-"
            print(f"\nResuming from {downloaded_bytes / (1024 * 1024):.1f} MB...")

        try:
            with requests.get(
                url,
                stream=True,
                headers=headers,
                timeout=(30, 300),
                allow_redirects=True
            ) as response:
                response.raise_for_status()

                if downloaded_bytes > 0 and response.status_code == 206:
                    mode = "ab"
                else:
                    mode = "wb"
                    downloaded_bytes = 0

                total_new = int(response.headers.get("content-length", 0))
                total_size = downloaded_bytes + total_new if total_new else 0

                with open(temp_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

                            if total_size > 0:
                                percent = (downloaded_bytes / total_size) * 100
                                print(f"\r{output_path.name}: {percent:.1f}% completed", end="")

            temp_path.replace(output_path)
            print(f"\nFinished: {output_path}")
            return True

        except Exception as e:
            print(f"\nAttempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Download failed after multiple retries.")
                return False

def main():
    for filename, url in FILES.items():
        save_path = RAW_DIR / filename

        if save_path.exists():
            print(f"Skipping {filename} (already exists)")
            continue

        print(f"\nStarting download: {filename}")
        success = download_with_resume(url, save_path)

        if not success:
            print(f"Could not finish downloading {filename}")

    print("\nSelected downloads completed.")

if __name__ == "__main__":
    main()