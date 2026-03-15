#!/usr/bin/env python3
"""
SIB-BatteryBERT — LLM Auto-Annotator (DEBUG VERSION)
Run from your project root:
    python annotation/scripts/annotator_LLM.py --limit 3
"""

import anthropic
import pandas as pd
import json
import re
import time
import argparse
import sys
from pathlib import Path
from tqdm import tqdm

INPUT_CSV       = "annotation/annotation_pool_1000.csv"
OUTPUT_JSON     = "annotation/sib_annotated_llm.json"
CHECKPOINT_FILE = "annotation/llm_annotate_checkpoint.json"
BATCH_SIZE      = 10
DELAY_SECONDS   = 1.0
MODEL           = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "You are an NER annotator for sodium-ion battery research. "
    "Respond with a single JSON array only. "
    "Do not write any text before or after the JSON. "
    "Do not use markdown code fences."
)

ANNOTATION_PROMPT = """\
Annotate named entities in each sentence. Use only these labels:
  MAT    = materials/chemicals (e.g. hard carbon, Na3V2(PO4)3, NaClO4)
  PROP   = electrochemical properties + numeric values with units (e.g. 320 mAh/g, 3.5 V, 85%)
  SYNTH  = synthesis methods/conditions (e.g. sol-gel, 800 C, ball milling)
  CHAR   = characterisation techniques (e.g. XRD, SEM, Raman, EIS)
  STRUCT = structural descriptors (e.g. P2-type, O3-type, layered oxide)
  APP    = device/application context (e.g. sodium-ion battery, full cell, SIB)

Return ONLY a JSON array like this (one object per sentence, in order):
[{{"idx":1,"spans":[{{"text":"hard carbon","label":"MAT","start":4,"end":15}}]}},{{"idx":2,"spans":[]}}]

Sentences:
{sentences}"""


def extract_json(text: str) -> list:
    print("\n" + "="*60)
    print("DEBUG — raw API response (repr):")
    print(repr(text))
    print("="*60 + "\n")

    text = text.strip()

    # Strategy 1: find first [ ... ] block
    bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
    if bracket_match:
        print(f"DEBUG — Strategy 1 matched: {repr(bracket_match.group()[:100])}")
        try:
            result = json.loads(bracket_match.group())
            print("DEBUG — Strategy 1 parsed OK")
            return result
        except json.JSONDecodeError as e:
            print(f"DEBUG — Strategy 1 failed: {e}")

    # Strategy 2: strip ALL markdown fences then parse
    cleaned = re.sub(r'```[a-zA-Z]*', '', text).replace('```', '').strip()
    print(f"DEBUG — Strategy 2 cleaned: {repr(cleaned[:100])}")
    try:
        result = json.loads(cleaned)
        print("DEBUG — Strategy 2 parsed OK")
        return result
    except json.JSONDecodeError as e:
        print(f"DEBUG — Strategy 2 failed: {e}")

    # Strategy 3: find every object with "idx" key
    objects = re.findall(r'\{[^{}]*"idx"[^{}]*\}', text, re.DOTALL)
    print(f"DEBUG — Strategy 3 found {len(objects)} objects")
    if objects:
        try:
            result = [json.loads(o) for o in objects]
            print("DEBUG — Strategy 3 parsed OK")
            return result
        except json.JSONDecodeError as e:
            print(f"DEBUG — Strategy 3 failed: {e}")

    raise ValueError(f"All strategies failed. Raw response:\n{text[:500]}")


def build_ls_task(sentence: str, doi: str, spans: list) -> dict:
    result = [
        {
            "id": f"span_{i}",
            "from_name": "label",
            "to_name": "text",
            "type": "labels",
            "value": {
                "start":  sp["start"],
                "end":    sp["end"],
                "text":   sp["text"],
                "labels": [sp["label"]]
            }
        }
        for i, sp in enumerate(spans)
    ]
    return {
        "data": {"sentence": sentence, "doi": doi},
        "predictions": [{"model_version": "claude-llm-v1", "result": result}]
    }


def annotate_batch(client, batch: list) -> list:
    numbered = "\n".join(f'{i+1}. "{row["sentence"]}"' for i, row in enumerate(batch))
    prompt = ANNOTATION_PROMPT.format(sentences=numbered)

    print(f"\nDEBUG — sending prompt (first 300 chars):\n{prompt[:300]}\n")

    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

    print(f"DEBUG — stop_reason: {message.stop_reason}")
    print(f"DEBUG — content blocks: {len(message.content)}")
    for i, block in enumerate(message.content):
        print(f"DEBUG — block[{i}] type={block.type}")

    raw = message.content[0].text
    parsed = extract_json(raw)

    idx_to_spans = {item["idx"]: item.get("spans", []) for item in parsed}
    return [idx_to_spans.get(i + 1, []) for i in range(len(batch))]


def load_checkpoint() -> list:
    p = Path(CHECKPOINT_FILE)
    return json.loads(p.read_text()) if p.exists() else []


def save_checkpoint(tasks: list):
    Path(CHECKPOINT_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(CHECKPOINT_FILE).write_text(json.dumps(tasks, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--input",   default=INPUT_CSV)
    parser.add_argument("--output",  default=OUTPUT_JSON)
    parser.add_argument("--limit",   type=int, default=None)
    parser.add_argument("--batch",   type=int, default=BATCH_SIZE)
    parser.add_argument("--delay",   type=float, default=DELAY_SECONDS)
    parser.add_argument("--resume",  action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)
    rows = df.to_dict("records")
    if args.limit:
        rows = rows[:args.limit]

    tasks = []
    start_idx = 0
    if args.resume:
        tasks = load_checkpoint()
        start_idx = len(tasks)
        print(f"[resume] Continuing from sentence {start_idx}")

    rows_to_process = rows[start_idx:]
    if not rows_to_process:
        print("Nothing to do — all sentences already annotated.")
        return

    client = anthropic.Anthropic(api_key=args.api_key) if args.api_key else anthropic.Anthropic()
    total = len(rows_to_process)
    total_spans = 0
    error_count = 0

    print(f"\nAnnotating {total} sentences in batches of {args.batch}...\n")

    for i in tqdm(range(0, total, args.batch), unit="batch"):
        batch = rows_to_process[i: i + args.batch]
        try:
            span_lists = annotate_batch(client, batch)
            for row, spans in zip(batch, span_lists):
                tasks.append(build_ls_task(row["sentence"], row.get("doi", ""), spans))
                total_spans += len(spans)
            tqdm.write(f"  batch {i//args.batch + 1}: {sum(len(s) for s in span_lists)} spans")
        except Exception as e:
            error_count += 1
            tqdm.write(f"[ERROR] batch {i//args.batch + 1}: {e}")
            for row in batch:
                tasks.append(build_ls_task(row["sentence"], row.get("doi", ""), []))

        save_checkpoint(tasks)
        if i + args.batch < total:
            time.sleep(args.delay)

        # # Only run ONE batch in debug mode then stop
        # print("\n[DEBUG MODE] Stopping after first batch. Check output above.")
        # break

    print(f"\n  Sentences processed : {len(tasks)}")
    print(f"  Spans found         : {total_spans}")
    print(f"  Errors              : {error_count}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(tasks, indent=2))
    print(f"\n  Saved → {out_path}\n")


if __name__ == "__main__":
    main()