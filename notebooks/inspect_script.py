# Run this in a notebook cell or as a script
import pandas as pd
df = pd.read_csv("data/processed/sentence_corpus.csv")
print(f"Total sentences: {len(df):,}")
print(f"Unique papers:   {df.doi.nunique():,}")
print(f"Avg length:      {df.char_len.mean():.0f} chars")
print()
# Print 30 random sentences to read manually
sample = df.sample(30, random_state=42)["sentence"]
for i, s in enumerate(sample, 1):
    print(f"{i:02d}. {s}")
    print()