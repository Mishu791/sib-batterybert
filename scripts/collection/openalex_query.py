# scripts/collection/openalex_query.py
import requests, time, pandas as pd, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.config import SIB_TITLE_KEYWORDS, OA_QUERIES

OA_BASE = "https://api.openalex.org/works"

def is_sib_title(title):
    if not title: return False
    return any(kw in title.lower() for kw in SIB_TITLE_KEYWORDS)

def reconstruct_abstract(inv_index):
    if not inv_index: return ""
    words = {}
    for word, positions in inv_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[k] for k in sorted(words))[:500]

def query_openalex(query, from_year=2015, to_year=2025):
    papers, cursor, accepted, rejected = [], "*", 0, 0
    print(f"  Querying OpenAlex: {query}")

    while True:
        params = {
            "search": query,
            "filter": f"publication_year:{from_year}-{to_year},type:article",
            "select": "doi,title,publication_year,cited_by_count,open_access,abstract_inverted_index",
            "per-page": 200,
            "cursor": cursor,
            "mailto": "your@gmail.com"
        }
        r = requests.get(OA_BASE, params=params)
        if r.status_code != 200: break
        data = r.json()
        batch = data.get("results", [])
        if not batch: break

        for item in batch:
            title = item.get("title", "") or ""
            # ── GATE 2: title check ───────────────────────
            if not is_sib_title(title):
                rejected += 1
                continue

            doi = (item.get("doi") or "").replace("https://doi.org/", "").lower().strip()
            oa_info = item.get("open_access") or {}
            oa_url = oa_info.get("oa_url") if oa_info.get("is_oa") else None

            papers.append({
                "doi": doi,
                "title": title,
                "year": item.get("publication_year"),
                "abstract": reconstruct_abstract(item.get("abstract_inverted_index")),
                "citations": item.get("cited_by_count", 0),
                "is_oa": bool(oa_url),
                "pdf_url": oa_url,
                "source": "openalex"
            })
            accepted += 1

        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor: break
        time.sleep(0.2)

    print(f"    → {accepted} accepted | {rejected} rejected by title")
    return papers

if __name__ == "__main__":
    all_papers = []
    for q in OA_QUERIES:
        papers = query_openalex(q)
        all_papers.extend(papers)

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset="doi")
    df = df[df["doi"] != ""]
    df.to_csv("data/raw_dois/openalex_papers.csv", index=False)
    print(f"OpenAlex FINAL: {len(df)} unique SIB papers")
