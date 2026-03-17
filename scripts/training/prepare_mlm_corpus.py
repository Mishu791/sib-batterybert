#!/usr/bin/env python3
"""
SIB-BatteryBERT — MLM Corpus Preparation
==========================================
Reads the GROBID sentence corpus, applies quality filters,
and writes a plain-text file (one sentence per line) for MLM pre-training.

Usage (run from project root):
    python training/scripts/prepare_mlm_corpus.py

    # Custom paths:
    python training/scripts/prepare_mlm_corpus.py \
        --input  data/processed/sib_sentences.csv \
        --output training/corpus_mlm.txt
"""

import pandas as pd
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input",  default="data/processed/sentence_corpus.csv")
parser.add_argument("--output", default="training/corpus_mlm.txt")
args = parser.parse_args()

print(f"\nReading {args.input} ...")
df = pd.read_csv(args.input)
print(f"  Raw rows : {len(df)}")

# ── Quality filters ───────────────────────────────────────────────────────────
df = df[df["sentence"].notna()]
df["sentence"] = df["sentence"].astype(str).str.strip()

# Length filter: 6–150 words
lengths = df["sentence"].str.split().str.len()
df = df[lengths.between(6, 150)]
print(f"  After length filter (6–150 words) : {len(df)}")

# Remove obvious GROBID artefacts
df = df[~df["sentence"].str.match(r"^\d+$")]           # pure numbers
df = df[~df["sentence"].str.match(r"^[\W\d\s]+$")]      # no letters at all
df = df[df["sentence"].str.len() > 20]                  # too short chars
print(f"  After artefact filter : {len(df)}")

# Deduplicate
df = df.drop_duplicates(subset="sentence")
print(f"  After dedup           : {len(df)}")

# ── Write output ──────────────────────────────────────────────────────────────
out = Path(args.output)
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", encoding="utf-8") as f:
    for sent in df["sentence"]:
        f.write(sent + "\n")

size_mb = out.stat().st_size / 1e6
print(f"\n  Sentences written : {len(df)}")
print(f"  File size         : {size_mb:.1f} MB")
print(f"  Saved             -> {out}\n")




