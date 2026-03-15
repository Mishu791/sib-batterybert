# scripts/annotation/prepare_annotation_pool.py
import pandas as pd
from pathlib import Path

Path("annotation").mkdir(exist_ok=True)

# Load your sentence corpus
df = pd.read_csv("data/processed/sentence_corpus.csv")

print(f"Total sentences available: {len(df):,}")
print(f"Columns: {df.columns.tolist()}")

# Prefer mid-length sentences — most entity-dense
filtered = df[df["char_len"].between(80, 400)].copy()
print(f"After length filter (80-400 chars): {len(filtered):,}")

# Sample 1,000 sentences
if len(filtered) >= 1000:
    pool = filtered.sample(1000, random_state=42)
else:
    pool = filtered
    print(f"Warning: only {len(pool)} sentences available — using all")

# Save annotation pool
pool[["doi", "sentence"]].reset_index(drop=True).to_csv(
    "annotation/annotation_pool_1000.csv", index=False
)

print(f"\nAnnotation pool saved: {len(pool)} sentences")
print(f"Saved to: annotation/annotation_pool_1000.csv")
print(f"\nSample sentences:")
for s in pool["sentence"].sample(5):
    print(f"  • {s[:100]}...")