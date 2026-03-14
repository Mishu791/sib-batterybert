# scripts/collection/download_pdfs.py
import requests, time, os, pandas as pd
from pathlib import Path
from tqdm import tqdm

DOWNLOAD_DIR = Path("data/pdfs_raw")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

FAILED_LOG = "data/raw_dois/failed_downloads.txt"
SUCCESS_LOG = "data/raw_dois/successful_downloads.txt"

HEADERS = {
    "User-Agent": "SIB-BatteryBERT-Research/1.0 (academic; mailto:dbmishu@gmail.com)"
}

def already_downloaded(doi):
    """Check if this DOI was already downloaded — allows safe resume."""
    safe_name = doi.replace("/", "_").replace(":", "_") + ".pdf"
    return (DOWNLOAD_DIR / safe_name).exists()

def download_pdf(row):
    doi = str(row["doi"])
    url = str(row["pdf_url"])
    safe_name = doi.replace("/", "_").replace(":", "_") + ".pdf"
    out_path = DOWNLOAD_DIR / safe_name

    try:
        r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        r.raise_for_status()

        # Verify it is actually a PDF
        content_type = r.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
            return False, "Not a PDF (wrong content type)"

        # Check file size (reject < 10KB = probably an error page)
        content = b""
        for chunk in r.iter_content(8192):
            content += chunk
            if len(content) > 50 * 1024 * 1024:  # 50MB cap
                return False, "File too large (>50MB)"

        if len(content) < 10240:
            return False, f"File too small ({len(content)} bytes)"

        out_path.write_bytes(content)
        return True, f"{len(content) // 1024}KB"

    except Exception as e:
        return False, str(e)[:100]

if __name__ == "__main__":
    df = pd.read_csv("data/raw_dois/pdf_download_list.csv")

    # Skip already downloaded
    df["skip"] = df["doi"].apply(already_downloaded)
    to_download = df[~df["skip"]]
    print(f"To download: {len(to_download)} | Already done: {df.skip.sum()}")

    success, failed = 0, 0

    with open(FAILED_LOG, "a") as fail_f, open(SUCCESS_LOG, "a") as succ_f:
        for _, row in tqdm(to_download.iterrows(), total=len(to_download)):
            ok, msg = download_pdf(row)
            if ok:
                success += 1
                succ_f.write(f"{row['doi']}\n")
            else:
                failed += 1
                fail_f.write(f"{row['doi']}\t{msg}\n")

            # Polite rate limit: 1 request per second
            time.sleep(1)

    print(f"\nDone: {success} downloaded, {failed} failed")
    print(f"PDFs saved to: {DOWNLOAD_DIR}/")
