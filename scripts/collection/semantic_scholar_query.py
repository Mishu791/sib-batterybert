# scripts/collection/semantic_scholar_query.py
import requests, time, random, pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.config import SIB_TITLE_KEYWORDS, SS_QUERIES

SS_API_KEY = None  # Set to your key string once received
SS_BASE    = "https://api.semanticscholar.org/graph/v1"
FIELDS     = "paperId,externalIds,title,abstract,year,citationCount,isOpenAccess,openAccessPdf"

def is_sib_title(title):
    if not title: return False
    return any(kw in title.lower() for kw in SIB_TITLE_KEYWORDS)

def search_ss(query, limit=100, offset=0):
    headers = {"x-api-key": SS_API_KEY} if SS_API_KEY else {}
    r = requests.get(
        f"{SS_BASE}/paper/search",
        params={"query": query, "fields": FIELDS,
                "limit": limit, "offset": offset},
        headers=headers,
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def collect_query(query, max_papers=1000):
    papers, offset, retries = [], 0, 0
    accepted, rejected = 0, 0
    print(f"  Querying SS: {query}")

    while len(papers) < max_papers:
        try:
            data = search_ss(query, offset=offset)
            batch = data.get("data", [])
            if not batch: break

            for p in batch:
                title = p.get("title", "") or ""
                # ── GATE 2: title check ───────────────────
                if not is_sib_title(title):
                    rejected += 1
                    continue

                doi = (p.get("externalIds") or {}).get("DOI", "")
                pdf_url = None
                if p.get("openAccessPdf"):
                    pdf_url = p["openAccessPdf"].get("url")

                papers.append({
                    "doi": doi.lower().strip() if doi else "",
                    "ss_id": p.get("paperId", ""),
                    "title": title,
                    "year": p.get("year"),
                    "abstract": (p.get("abstract") or "")[:500],
                    "citations": p.get("citationCount", 0),
                    "is_oa": p.get("isOpenAccess", False),
                    "pdf_url": pdf_url,
                    "source": "semantic_scholar"
                })
                accepted += 1

            offset += len(batch)
            retries = 0
            time.sleep(2)

        except Exception as e:
            if "429" in str(e):
                wait = (2 ** retries) + random.uniform(1, 3)
                print(f"    Rate limited. Waiting {wait:.1f}s...")
                time.sleep(wait)
                retries += 1
                if retries > 5: break
            else:
                print(f"    Error: {e}")
                break

    print(f"    → {accepted} accepted | {rejected} rejected by title")
    return papers

if __name__ == "__main__":
    all_papers = []
    for q in SS_QUERIES:
        papers = collect_query(q)
        all_papers.extend(papers)
        time.sleep(5)

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset=["ss_id"])
    df.to_csv("data/raw_dois/semantic_scholar_papers.csv", index=False)
    oa = df["is_oa"].sum()
    pdf = df["pdf_url"].notna().sum()
    print(f"SS FINAL: {len(df)} papers | OA: {oa} | PDFs: {pdf}")
