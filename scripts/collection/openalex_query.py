# scripts/collection/openalex_query.py
import requests, time, pandas as pd
from pathlib import Path

OA_BASE = "https://api.openalex.org/works"

QUERIES = [
    "sodium-ion battery", "Na-ion battery",
    "sodium ion cathode", "hard carbon sodium",
    "Prussian blue analogue sodium"
]

def query_openalex(query, from_year=2015, to_year=2025):
    papers = []
    cursor = "*"
    print(f"Querying OpenAlex: {query}")

    while True:
        params = {
            "search": query,
            "filter": f"publication_year:{from_year}-{to_year},type:article",
            "select": "doi,title,publication_year,primary_location,cited_by_count,open_access,abstract_inverted_index",
            "per-page": 200,
            "cursor": cursor,
            "mailto": "your@email.com"
        }
        r = requests.get(OA_BASE, params=params)
        if r.status_code != 200:
            break
        data = r.json()
        batch = data.get("results", [])
        if not batch:
            break
        papers.extend(batch)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.2)
    return papers

def reconstruct_abstract(inverted_index):
    """OpenAlex stores abstracts as inverted index. Reconstruct."""
    if not inverted_index:
        return ""
    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[k] for k in sorted(words.keys()))[:500]

def normalize_oa(paper):
    doi = (paper.get("doi") or "").replace("https://doi.org/", "").lower().strip()
    journal = ""
    loc = paper.get("primary_location") or {}
    if loc.get("source"):
        journal = loc["source"].get("display_name", "")
    oa_url = None
    if paper.get("open_access", {}).get("is_oa"):
        oa_url = paper["open_access"].get("oa_url")

    return {
        "doi": doi,
        "title": paper.get("title", ""),
        "year": paper.get("publication_year"),
        "journal": journal,
        "abstract": reconstruct_abstract(paper.get("abstract_inverted_index")),
        "citations": paper.get("cited_by_count", 0),
        "is_oa": bool(oa_url),
        "pdf_url": oa_url,
        "source": "openalex"
    }

if __name__ == "__main__":
    all_papers = []
    for q in QUERIES:
        papers = query_openalex(q)
        normalized = [normalize_oa(p) for p in papers]
        all_papers.extend(normalized)
        print(f"  → {len(normalized)} papers")

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset="doi")
    df = df[df["doi"] != ""]
    df.to_csv("data/raw_dois/openalex_papers.csv", index=False)
    print(f"Total unique from OpenAlex: {len(df)}")
