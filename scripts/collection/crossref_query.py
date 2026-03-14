# scripts/collection/crossref_query.py
from habanero import Crossref
import pandas as pd, time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from scripts.config import SIB_TITLE_KEYWORDS, CROSSREF_QUERIES

cr = Crossref(mailto="dbmishu@gmail.com")

def is_sib_title(title):
    """Gate 2: title must contain at least one SIB keyword."""
    if not title:
        return False
    title_lower = title.lower()
    return any(kw in title_lower for kw in SIB_TITLE_KEYWORDS)

def normalize_paper(item):
    try:
        title_raw = item.get("title", "") or ""
        title = title_raw[0] if isinstance(title_raw, list) else title_raw

        # ── GATE 2: reject if title is not SIB ───────────────
        if not is_sib_title(title):
            return None

        year = None
        pub = item.get("published") or item.get("published-print") or {}
        parts = pub.get("date-parts", [[None]])
        if parts and parts[0]:
            year = parts[0][0]

        return {
            "doi": item.get("DOI", "").lower().strip(),
            "title": title,
            "year": year,
            "abstract": (item.get("abstract") or "")[:500],
            "citations": item.get("is-referenced-by-count", 0),
            "source": "crossref"
        }
    except Exception as e:
        return None

def query_crossref(query, from_year=2015, to_year=2024):
    results = []
    offset = 0
    rejected = 0
    print(f"  Querying: {query}")

    while offset < 9900:
        try:
            res = cr.works(
                query=query,
                filter={"from-pub-date": str(from_year),
                        "until-pub-date": str(to_year),
                        "type": "journal-article"},
                limit=100,
                offset=offset,
                select=["DOI","title","published","abstract","is-referenced-by-count"]
            )
            items = res["message"]["items"]
            if not items:
                break

            for item in items:
                paper = normalize_paper(item)
                if paper and paper["doi"]:
                    results.append(paper)
                else:
                    rejected += 1

            offset += len(items)
            if offset >= min(res["message"]["total-results"], 9900):
                break
            time.sleep(0.3)

        except Exception as e:
            print(f"    Error at offset {offset}: {e}")
            break

    print(f"    → {len(results)} accepted | {rejected} rejected by title")
    return results

if __name__ == "__main__":
    all_papers = []
    for q in CROSSREF_QUERIES:
        papers = query_crossref(q)
        all_papers.extend(papers)
        time.sleep(1)

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset="doi")
    df = df[df["doi"] != ""]
    df.to_csv("data/raw_dois/crossref_papers.csv", index=False)
    print(f"\nCrossRef FINAL: {len(df)} unique SIB papers")