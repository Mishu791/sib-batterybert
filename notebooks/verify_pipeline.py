# scripts/collection/verify_pipeline.py
# Run this after each stage to confirm quality
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, ".")
from scripts.config import SIB_TITLE_KEYWORDS

def check_sib(title):
    if not title or not isinstance(title, str): return False
    return any(kw in title.lower() for kw in SIB_TITLE_KEYWORDS)

print("=" * 60)
print("PIPELINE QUALITY VERIFICATION")
print("=" * 60)

# Check 1: sib_paper_database.csv
if Path("data/metadata/sib_paper_database.csv").exists():
    df = pd.read_csv("data/metadata/sib_paper_database.csv")
    sib_pct = df["title"].apply(check_sib).mean() * 100
    print(f"Database: {len(df):,} papers | SIB title match: {sib_pct:.1f}%")
    print(f"  PDF URLs available: {df.pdf_url.notna().sum():,}")

# Check 2: pdf_download_list.csv
if Path("data/raw_dois/pdf_download_list.csv").exists():
    df = pd.read_csv("data/raw_dois/pdf_download_list.csv")
    sib_pct = df["title"].apply(check_sib).mean() * 100
    print(f"Download list: {len(df):,} papers | SIB title match: {sib_pct:.1f}%")

# Check 3: downloaded PDFs
pdf_dir = Path("data/pdfs_raw")
if pdf_dir.exists():
    pdfs = list(pdf_dir.glob("*.pdf"))
    print(f"Downloaded PDFs: {len(pdfs):,}")
    print("Sample filenames:")
    for p in pdfs[:5]:
        print(f"  {p.name[:80]}")

# Check 4: parsed JSON files
json_dir = Path("data/processed")
if json_dir.exists():
    import json
    jsons = list(json_dir.glob("*.json"))
    print(f"Parsed JSON files: {len(jsons):,}")
    sib_count = 0
    for jf in jsons[:50]:  # sample 50
        with open(jf) as f:
            d = json.load(f)
        if check_sib(d.get("title", "")):
            sib_count += 1
    print(f"  Sample check: {sib_count}/50 are SIB papers")

print("=" * 60)
print("Target: ALL stages should show 95%+ SIB title match")
