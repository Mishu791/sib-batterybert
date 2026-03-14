# scripts/collection/merge_doi_database.py
import pandas as pd
import requests, time, pandas as pd, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.config import SIB_TITLE_KEYWORDS

cr = pd.read_csv("data/raw_dois/crossref_papers.csv")
ss = pd.read_csv("data/raw_dois/semantic_scholar_papers.csv")
oa = pd.read_csv("data/raw_dois/openalex_papers.csv")

common = ["doi", "title", "year", "abstract", "citations", "is_oa", "pdf_url", "source"]
for df in [cr, ss, oa]:
    for col in common:
        if col not in df.columns: df[col] = None

merged = pd.concat([ss[common], oa[common], cr[common]])
merged["doi"] = merged["doi"].str.lower().str.strip()
merged = merged[merged["doi"].notna() & (merged["doi"] != "")]
merged = merged.drop_duplicates(subset="doi", keep="first")

# ── FINAL TITLE QUALITY CHECK ────────────────────────────
def is_sib_title(title):
    if not title or not isinstance(title, str): return False
    return any(kw in title.lower() for kw in SIB_TITLE_KEYWORDS)

before = len(merged)
merged = merged[merged["title"].apply(is_sib_title)]
after = len(merged)
print(f"Final title gate removed: {before - after} papers")

merged.to_csv("data/metadata/sib_paper_database.csv", index=False)

print("=" * 55)
print(f"VERIFIED SIB papers:        {len(merged):>10,}")
print(f"With PDF URL:               {merged.pdf_url.notna().sum():>10,}")
print(f"Year range:                 {int(merged.year.min())} - {int(merged.year.max())}")
print("=" * 55)

# Spot check: print 10 random titles to verify manually
print("\nRandom sample of 10 titles — verify these look correct:")
for t in merged["title"].dropna().sample(10, random_state=42):
    print(f"  ✓ {t[:90]}")
