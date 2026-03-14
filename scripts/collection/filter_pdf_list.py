# scripts/collection/filter_pdf_list.py
import pandas as pd

df = pd.read_csv("data/metadata/sib_paper_database.csv")
#print(df.columns.tolist())
#print(df.head(2))

# Step 1: Keep only rows that have a PDF URL
pdf_df = df[df["pdf_url"].notna() & (df["pdf_url"] != "")].copy()
print(f"Papers with PDF URL: {len(pdf_df)}")

# Step 2: Filter to 2015-2025 (most relevant SIB research era)
pdf_df = pdf_df[pdf_df["year"].between(2015, 2025)]
print(f"After year filter (2015-2024): {len(pdf_df)}")

# Step 3: Remove rows where pdf_url looks invalid
pdf_df = pdf_df[pdf_df["pdf_url"].str.startswith("http")]
print(f"After URL validity check: {len(pdf_df)}")

# Step 4: Sort by citation count descending (most-cited = highest quality)
pdf_df = pdf_df.sort_values("citations", ascending=False)

# Step 5: Sample top 5,000 by citation count
# These are the most impactful papers in the field
download_list = pdf_df.head(5000)

# Replace the broken line with this
desired_cols = ["doi", "title", "year", "journal", "citations", "pdf_url"]
available_cols = [c for c in desired_cols if c in download_list.columns]
missing = [c for c in desired_cols if c not in download_list.columns]

if missing:
    print(f"Warning: these columns not found and will be skipped: {missing}")

download_list[available_cols].to_csv(
    "data/raw_dois/pdf_download_list.csv", index=False
)

print(f"\nFinal download list: {len(download_list)} papers")
print(f"Columns saved: {available_cols}")


print(f"\nFinal download list: {len(download_list)} papers")
print(f"Year range: {download_list.year.min():.0f} - {download_list.year.max():.0f}")
print(f"Sources represented: {download_list.source.value_counts().to_dict()}")

