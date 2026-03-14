# scripts/collection/merge_doi_database.py
import pandas as pd

# Load all three sources
cr = pd.read_csv("data/raw_dois/crossref_dois.csv")
ss = pd.read_csv("data/raw_dois/semantic_scholar_papers.csv")
oa = pd.read_csv("data/raw_dois/openalex_papers.csv")

# Standardize columns
common_cols = ["doi", "title", "year", "abstract", "citations", "is_oa", "pdf_url", "source"]

for df in [cr, ss, oa]:
    for col in common_cols:
        if col not in df.columns:
            df[col] = None

# Merge: prefer SS data (better abstracts), fall back to CrossRef
merged = pd.concat([ss[common_cols], oa[common_cols], cr[common_cols]])
merged["doi"] = merged["doi"].str.lower().str.strip()
merged = merged[merged["doi"].notna() & (merged["doi"] != "")]

# Keep first occurrence (SS > OA > CrossRef preference)
merged = merged.drop_duplicates(subset="doi", keep="first")
merged = merged.sort_values("year", ascending=True)

# Save final database
merged.to_csv("data/metadata/sib_paper_database.csv", index=False)

# Print statistics (this goes in your README)
print("=" * 50)
print(f"Total unique SIB papers: {len(merged)}")
print(f"Year range: {merged.year.min()} - {merged.year.max()}")
print(f"Open access: {merged.is_oa.sum()} ({merged.is_oa.mean()*100:.1f}%)")
print(f"PDFs available: {merged.pdf_url.notna().sum()}")
print(f"Papers with abstract: {merged.abstract.notna().sum()}")
print("=" * 50)
print(merged.groupby("year").size().tail(10))  # papers per year
