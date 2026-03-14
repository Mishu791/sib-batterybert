# scripts/collection/crossref_query.py
from habanero import Crossref
import pandas as pd
import time, json
from pathlib import Path

cr = Crossref(mailto="dbmishu@gmail.com")  # polite pool = faster

QUERIES = [
    "sodium-ion battery",
    "Na-ion battery",
    "sodium ion battery cathode",
    "hard carbon sodium anode",
    "Prussian blue analogue sodium battery",
    "NASICON sodium electrolyte",
    "P2-type sodium layered oxide"
]

def query_crossref(query, from_year=2015, to_year=2025):
    results = []
    offset = 0
    print(f"Querying: {query}")

    while True:
        try:
            res = cr.works(
                query=query,
                filter={"from-pub-date": str(from_year),
                        "until-pub-date": str(to_year),
                        "type": "journal-article"},
                limit=100,
                offset=offset,
                select=["DOI","title","published","abstract",
                        "container-title","is-referenced-by-count"]
            )
            items = res["message"]["items"]
            if not items:
                break
            results.extend(items)
            offset += len(items)
            if offset >= res["message"]["total-results"]:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error at offset {offset}: {e}")
            break
    return results

def normalize_paper(item):
    try:
        title_raw = item.get("title", "") or ""
        title = title_raw[0] if isinstance(title_raw, list) else title_raw

        year = None
        pub = item.get("published") or item.get("published-print") or {}
        parts = pub.get("date-parts", [[None]])
        if parts and parts[0]:
            year = parts[0][0]

        journal_raw = item.get("container-title") or [""]
        journal = journal_raw[0] if isinstance(journal_raw, list) else str(journal_raw)

        return {
            "doi": item.get("DOI", "").lower().strip(),
            "title": title,
            "year": year,
            "journal": journal,
            "abstract": (item.get("abstract") or "")[:500],
            "citations": item.get("is-referenced-by-count", 0),
            "source": "crossref"
        }
    except Exception as e:
        print(f"  Skipping malformed record: {e}")
        return None

if __name__ == "__main__":
    Path("data/raw_dois").mkdir(parents=True, exist_ok=True)
    all_papers = []

    for q in QUERIES:
        papers = query_crossref(q)
        normalized = [normalize_paper(p) for p in papers]
        normalized = [p for p in normalized if p is not None]  # filter failed records
        all_papers.extend(normalized)
        print(f"  → {len(normalized)} papers")
        time.sleep(1)

    df = pd.DataFrame(all_papers)
    df = df.drop_duplicates(subset="doi")
    df = df[df["doi"] != ""]
    df.to_csv("data/raw_dois/crossref_dois.csv", index=False)
    print(f"\nTotal unique DOIs from CrossRef: {len(df)}")
