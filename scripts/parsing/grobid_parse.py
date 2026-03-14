# scripts/parsing/grobid_parse.py
import os, json, time, re
from pathlib import Path
from tqdm import tqdm
import xml.etree.ElementTree as ET
import requests

GROBID_URL = "http://localhost:8070"
PDF_DIR    = Path("data/pdfs_raw")
OUT_DIR    = Path("data/processed")
FAILED_LOG = Path("data/processed/failed_grobid.txt")
REJECTED_LOG = Path("data/processed/rejected_offtopic.txt")  # new

OUT_DIR.mkdir(parents=True, exist_ok=True)

NS = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace"
}

# ── SIB title filter ──────────────────────────────────────────────────────────
TITLE_KEYWORDS = [
    "sodium-ion", "na-ion", "sodium ion battery",
    "sodium ion cathode", "sodium ion anode",
    "hard carbon", "prussian blue",
    "nasicon", "p2-type", "o3-type", "p3-type",
    "sodium cathode", "sodium anode", "sodium electrolyte",
    "sodium storage", "layered oxide",
    "sodium battery", "na battery",
    "sodium metal", "na metal",
    "sodium intercalation", "sodium insertion",
]

def is_sib_paper(title):
    if not title:
        return False
    title_lower = title.lower()
    return any(kw in title_lower for kw in TITLE_KEYWORDS)

# ─────────────────────────────────────────────────────────────────────────────

def check_grobid_alive():
    try:
        r = requests.get(f"{GROBID_URL}/api/isalive", timeout=5)
        return r.text.strip() == "true"
    except:
        return False

def parse_tei_xml(xml_text, doi):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return None, f"XML parse error: {e}"

    result = {"doi": doi, "title": "", "abstract": "",
              "sections": [], "sentences": []}

    title_el = root.find(".//tei:titleStmt/tei:title", NS)
    if title_el is not None and title_el.text:
        result["title"] = title_el.text.strip()

    # ── Reject off-topic papers immediately after extracting title ────────────
    if not is_sib_paper(result["title"]):
        return None, f"OFFTOPIC: {result['title'][:80]}"

    abstract_el = root.find(".//tei:abstract", NS)
    if abstract_el is not None:
        abstract_text = " ".join(
            (p.text or "") for p in abstract_el.findall(".//tei:p", NS)
        ).strip()
        result["abstract"] = abstract_text

    body = root.find(".//tei:body", NS)
    if body is not None:
        for div in body.findall(".//tei:div", NS):
            section = {"heading": "", "paragraphs": []}

            head = div.find("tei:head", NS)
            if head is not None and head.text:
                section["heading"] = head.text.strip()

            for para in div.findall("tei:p", NS):
                text = "".join(para.itertext()).strip()
                text = re.sub(r"\s+", " ", text)
                if len(text) > 30:
                    section["paragraphs"].append(text)

            if section["paragraphs"]:
                result["sections"].append(section)

    all_text = result["abstract"]
    for sec in result["sections"]:
        heading_lower = sec["heading"].lower()
        if any(skip in heading_lower for skip in
               ["reference", "acknowledg", "funding", "conflict"]):
            continue
        all_text += " " + " ".join(sec["paragraphs"])

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", all_text)
    sentences = [s.strip() for s in sentences
                 if 20 < len(s.strip()) < 1000]
    result["sentences"] = list(dict.fromkeys(sentences))

    return result, None

def process_pdf(pdf_path):
    doi = pdf_path.stem.replace("_", "/", 1)

    with open(pdf_path, "rb") as f:
        files = {"input": (pdf_path.name, f, "application/pdf")}
        try:
            r = requests.post(
                f"{GROBID_URL}/api/processFulltextDocument",
                files=files,
                data={"consolidateHeader": "1"},
                timeout=120
            )
            r.raise_for_status()
        except requests.exceptions.Timeout:
            return None, "Timeout after 120s"
        except Exception as e:
            return None, str(e)[:100]

    return parse_tei_xml(r.text, doi)

if __name__ == "__main__":
    if not check_grobid_alive():
        print("ERROR: GROBID is not running!")
        print("Start it with: docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.0")
        exit(1)
    print("GROBID is running ✓")

    pdfs = list(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to process")

    already_done = set(f.stem for f in OUT_DIR.glob("*.json"))
    pdfs = [p for p in pdfs if p.stem not in already_done]
    print(f"Skipping {len(already_done)} already processed | Remaining: {len(pdfs)}")

    success, failed, rejected = 0, 0, 0

    with open(FAILED_LOG, "a") as fail_f, open(REJECTED_LOG, "a") as rej_f:
        for pdf_path in tqdm(pdfs, desc="Parsing PDFs"):
            result, error = process_pdf(pdf_path)

            if result and result["sentences"]:
                out_file = OUT_DIR / (pdf_path.stem + ".json")
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                success += 1
            elif error and error.startswith("OFFTOPIC:"):
                rej_f.write(f"{pdf_path.name}\t{error}\n")
                rejected += 1
            else:
                fail_f.write(f"{pdf_path.name}\t{error or 'no sentences extracted'}\n")
                failed += 1

            time.sleep(0.2)

    print(f"\nDone:")
    print(f"  Saved (SIB papers):    {success:>6,}")
    print(f"  Rejected (off-topic):  {rejected:>6,}")
    print(f"  Failed (parse errors): {failed:>6,}")
    print(f"\nJSON files saved to: {OUT_DIR}/")