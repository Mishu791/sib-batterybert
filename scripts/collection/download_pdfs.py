# scripts/collection/download_pdfs.py
import requests, time, os, re, pandas as pd
from pathlib import Path
from tqdm import tqdm

DOWNLOAD_DIR = Path("data/pdfs_raw")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "SIB-BatteryBERT/1.0 (academic; mailto:dbmishu@gmail.com)"}

def safe_filename(doi, title):
    """Create readable filename: doi_slug + title_slug."""
    doi_slug = re.sub(r"[^a-z0-9]", "_", doi.lower())[:40]
    title_slug = re.sub(r"[^a-z0-9 ]", "", title.lower())
    title_slug = "_".join(title_slug.split()[:5])  # first 5 words
    return f"{doi_slug}_{title_slug}.pdf"

def already_downloaded(doi, title):
    fname = safe_filename(doi, title)
    return (DOWNLOAD_DIR / fname).exists()

def download_pdf(row):
    doi = str(row["doi"])
    title = str(row["title"])
    url = str(row["pdf_url"])
    fname = safe_filename(doi, title)
    out_path = DOWNLOAD_DIR / fname

    try:
        r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        r.raise_for_status()

        content_type = r.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return False, "Not a PDF"

        content = b""
        for chunk in r.iter_content(8192):
            content += chunk
            if len(content) > 50 * 1024 * 1024:
                return False, "Too large (>50MB)"

        if len(content) < 10240:
            return False, f"Too small ({len(content)} bytes)"

        out_path.write_bytes(content)
        return True, f"{len(content)//1024}KB"

    except Exception as e:
        return False, str(e)[:80]

if __name__ == "__main__":
    df = pd.read_csv("data/raw_dois/pdf_download_list.csv")
    df["skip"] = df.apply(lambda r: already_downloaded(r["doi"], r["title"]), axis=1)
    to_dl = df[~df["skip"]]
    print(f"To download: {len(to_dl)} | Already done: {df.skip.sum()}")

    success, failed = 0, 0

    with open("data/raw_dois/failed_downloads.txt", "a") as fail_f:
        for _, row in tqdm(to_dl.iterrows(), total=len(to_dl)):
            ok, msg = download_pdf(row)
            if ok:
                success += 1
            else:
                failed += 1
                fail_f.write(f"{row['doi']}\t{row['title'][:60]}\t{msg}\n")
            time.sleep(1)

    print(f"Done: {success} downloaded, {failed} failed")

    # Spot check: list first 20 downloaded filenames
    print("\nFirst 20 downloaded files (verify titles look SIB-relevant):")
    for f in list(DOWNLOAD_DIR.glob("*.pdf"))[:20]:
        print(f"  {f.name[:80]}")