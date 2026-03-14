# scripts/collection/semantic_scholar_query.py
import requests, time, pandas as pd
from pathlib import Path

SS_BASE = "https://api.semanticscholar.org/graph/v1"

# Semantic Scholar field list — exactly what we need
FIELDS = "paperId,externalIds,title,abstract,year,journal,citationCount,isOpenAccess,openAccessPdf"

QUERIES = [
    "sodium ion battery", "Na-ion battery cathode",
    "hard carbon sodium anode", "NASICON sodium",
    "P2 type layered oxide sodium", "Prussian blue sodium battery"
]

def search_semantic_scholar(query, limit=100, offset=0):
    url = f"{SS_BASE}/paper/search"
    params = {
        "query": query,
        "fields": FIELDS,
        "limit": limit,
        "offset": offset
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

def collect_all(query, max_papers=1000):
    papers = []
    offset = 0
    while len(papers) < max_papers:
        try:
            data = search_semantic_scholar(query, offset=offset)
            batch = data.get("data", [])
            if not batch:
                break
            papers.extend(batch)
            offset += len(batch)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error at offset {offset}: {e}")
            break
    return papers

def normalize_ss(paper):
    doi = (paper.get("externalIds") or {}).get("DOI", "")
    pdf_url = None
    if paper.get("openAccessPdf"):
        pdf_url = paper["openAccessPdf"].get("url")

    return {
        "doi": doi.lower().strip() if doi else "",
        "ss_id": paper.get("paperId", ""),
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "abstract": (paper.get("abstract") or "")[:500],
        "citations": paper.get("citationCount", 0),
        "is_oa": paper.get("isOpenAccess", False),
        "pdf_url": pdf_url,  # GOLD: legal full text for Week 2
        "source": "semantic_scholar"
    }

if __name__ == "__main__":
    all_papers = []
    for q in QUERIES:
        print(f"Querying SS: {q}")
        papers = collect_all(q)
        normalized = [normalize_ss(p) for p in papers]
        all_papers.extend(normalized)
        print(f"  → {len(normalized)} papers")
        time.sleep(2)

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset=["ss_id"])
    df.to_csv("data/raw_dois/semantic_scholar_papers.csv", index=False)

    oa_count = df["is_oa"].sum()
    pdf_count = df["pdf_url"].notna().sum()
    print(f"Total: {len(df)} | Open Access: {oa_count} | PDFs available: {pdf_count}")