# scripts/collection/filter_pdf_list.py
import pandas as pd
import requests, time, pandas as pd, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.config import SIB_TITLE_KEYWORDS

df = pd.read_csv("data/metadata/sib_paper_database.csv")

# ── GATE 3a: must have PDF URL ───────────────────────────
pdf_df = df[df["pdf_url"].notna() & df["pdf_url"].str.startswith("http")]
print(f"With valid PDF URL: {len(pdf_df)}")

# ── GATE 3b: year range ──────────────────────────────────
pdf_df = pdf_df[pdf_df["year"].between(2015, 2026)]
print(f"After year filter (2015-2026): {len(pdf_df)}")

# ── GATE 3c: title must pass SIB check again ─────────────
# This catches any papers that slipped through with null titles earlier
pdf_df = pdf_df[pdf_df["title"].apply(
    lambda t: any(kw in str(t).lower() for kw in SIB_TITLE_KEYWORDS)
)]
print(f"After title re-validation: {len(pdf_df)}")

# Sort by citations — most impactful papers first
pdf_df = pdf_df.sort_values("citations", ascending=False)

# Take top 3,000 — enough for MLM training, manageable for GROBID
download_list = pdf_df.head(3000)

download_list[["doi", "title", "year", "citations", "pdf_url", "source"]].to_csv(
    "data/raw_dois/pdf_download_list.csv", index=False
)

print(f"\nDownload list: {len(download_list)} papers")
print(f"Year range: {download_list.year.min():.0f} - {download_list.year.max():.0f}")
print(f"Sources: {download_list.source.value_counts().to_dict()}")
print("\nSample of 10 titles being downloaded:")
for t in download_list["title"].head(10):
    print(f"  • {t[:85]}")

