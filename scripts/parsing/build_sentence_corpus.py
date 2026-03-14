# scripts/parsing/build_sentence_corpus.py
import json, re, pandas as pd
from pathlib import Path
from tqdm import tqdm

JSON_DIR = Path("data/processed")
OUT_FILE = Path("data/processed/sentence_corpus.csv")

# ── Paper-level title filter ───────────────────────────────────────────────────
# A JSON file is accepted ONLY if its title contains at least one of these
TITLE_KEYWORDS = [
    "sodium-ion", "na-ion", "sodium ion battery",
    "sodium ion cathode", "sodium ion anode",
    "hard carbon", "prussian blue",
    "nasicon", "p2-type", "o3-type", "p3-type",
    "sodium cathode", "sodium anode", "sodium electrolyte",
    "sodium storage", "layered oxide",
    "sodium battery", "na battery",
    "sib cathode", "sib anode",
    "sodium metal", "na metal",
    "sodium intercalation", "sodium insertion",
]

# ── Sentence-level SIB filter ─────────────────────────────────────────────────
# After the paper passes title filter, sentences must still match
SIB_SPECIFIC = [
    "sodium-ion", "na-ion", "sodium ion",
    "hard carbon", "prussian blue", "nasicon",
    "p2-type", "p3-type", "o3-type",
    "sodium cathode", "sodium anode", "sodium electrolyte",
    "sodium storage", "sodium insertion", "sodium intercalation",
    "na+ ", "na+)", "na0.", "na2/3", "na0.67",
    "sodium metal", "sib ",
    "namno", "nafepo", "naco", "nafep",
    "sodium layered", "layered oxide sodium",
]

# ── Boilerplate patterns ──────────────────────────────────────────────────────
BOILERPLATE = [
    r"this article is licensed under",
    r"creative commons attribution",
    r"all rights reserved",
    r"doi:\s*10\.\d+",
    r"received:\s*\d+",
    r"accepted:\s*\d+",
    r"©\s*20\d\d",
    r"downloaded from",
    r"^fig\.?\s*\d+",
    r"^table\s*\d+",
    r"^scheme\s*\d+",
]


def is_sib_paper(title):
    """Return True if the paper title matches SIB topics."""
    if not title:
        return False
    title_lower = title.lower()
    return any(kw in title_lower for kw in TITLE_KEYWORDS)


def is_sib_sentence(text):
    """Return True if the sentence contains SIB-specific content."""
    text_lower = text.lower()
    return any(term in text_lower for term in SIB_SPECIFIC)


def is_boilerplate(text):
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in BOILERPLATE)


def clean_sentence(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s([a-z])", r"\1", text)
    text = re.sub(r"\[\d+(?:,\d+)*\]", "", text)
    text = re.sub(r"\(\d+\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


if __name__ == "__main__":
    json_files = list(JSON_DIR.glob("*.json"))
    print(f"Total JSON files found: {len(json_files)}")

    all_sentences = []
    papers_accepted = 0
    papers_rejected = 0
    rejected_offtopic = 0
    rejected_boilerplate = 0
    rejected_length = 0

    for jf in tqdm(json_files):
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # ── GATE 1: reject entire paper if title is off-topic ─────────────────
        title = data.get("title", "")
        if not is_sib_paper(title):
            papers_rejected += 1
            continue

        papers_accepted += 1
        doi = data.get("doi", "")

        for sent in data.get("sentences", []):
            cleaned = clean_sentence(sent)

            # ── GATE 2: length filter ─────────────────────────────────────────
            if len(cleaned) < 40 or len(cleaned) > 600:
                rejected_length += 1
                continue

            # ── GATE 3: boilerplate filter ────────────────────────────────────
            if is_boilerplate(cleaned):
                rejected_boilerplate += 1
                continue

            # ── GATE 4: sentence must be SIB-relevant ─────────────────────────
            if not is_sib_sentence(cleaned):
                rejected_offtopic += 1
                continue

            all_sentences.append({
                "doi": doi,
                "title": title,
                "sentence": cleaned,
                "char_len": len(cleaned)
            })

    df = pd.DataFrame(all_sentences)
    df = df.drop_duplicates(subset="sentence")
    df = df.sort_values("char_len").reset_index(drop=True)

    df.to_csv(OUT_FILE, index=False)

    print(f"\n{'=' * 55}")
    print(f"Papers accepted (SIB title match): {papers_accepted:>8,}")
    print(f"Papers rejected (off-topic title): {papers_rejected:>8,}")
    print(f"{'─' * 55}")
    print(f"Sentences extracted (final):       {len(df):>8,}")
    print(f"Unique papers contributing:        {df.doi.nunique():>8,}")
    print(f"Avg sentence length:               {df.char_len.mean():>8.0f} chars")
    print(f"{'─' * 55}")
    print(f"Rejected (off-topic sentence):     {rejected_offtopic:>8,}")
    print(f"Rejected (boilerplate):            {rejected_boilerplate:>8,}")
    print(f"Rejected (too short/long):         {rejected_length:>8,}")
    print(f"{'=' * 55}")
    print(f"\nSaved to: {OUT_FILE}")

    # Show accepted paper titles so you can verify quality
    print(f"\nSample of accepted paper titles:")
    accepted_titles = df["title"].drop_duplicates().sample(min(10, df["title"].nunique()))
    for t in accepted_titles:
        print(f"  ✓ {t[:90]}")