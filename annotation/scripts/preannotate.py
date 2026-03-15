# scripts/annotation/preannotate.py
import spacy
import pandas as pd
import json
from pathlib import Path
from tqdm import tqdm

nlp = spacy.load("en_core_web_sm")

# Patterns for rule-based pre-annotation
# These cover the most common SIB entities reliably
import re

# Common SIB material patterns
MAT_PATTERNS = [
    r'\bhard carbon\b',
    r'\bprussian blue analogue\b',
    r'\bprussian blue analog\b',
    r'\bNASICON\b',
    r'\bNa[0-9][\w\.]+',        # sodium compound formulas
    r'\bNaMnO[0-9]?\b',
    r'\bNaFePO[0-9]\b',
    r'\bNa[0-9]\.[0-9]+\w+',    # Na0.67... type formulas
]

# Crystal structure patterns
STRUCT_PATTERNS = [
    r'\bP2-type\b', r'\bO3-type\b', r'\bP3-type\b',
    r'\bP2 type\b', r'\bO3 type\b',
    r'\blayered oxide\b',
    r'\btunnel structure\b',
]

# Property patterns (number + unit)
PROP_PATTERNS = [
    r'\d+\.?\d*\s*mAh/g',
    r'\d+\.?\d*\s*mAh\s*/\s*g',
    r'\d+\.?\d*\s*%\s*ICE',
    r'\d+\.?\d*\s*%\s*coulombic',
    r'\d+\s*cycles',
    r'\d+\.?\d*\s*[Vv]\s*vs',
    r'\d+\.?\d*\s*C\s+rate',
    r'\d+\.?\d*\s*Wh/kg',
]

# Synthesis patterns
SYNTH_PATTERNS = [
    r'\d+\s*°C',
    r'\bsol-gel\b', r'\bball.?milling\b',
    r'\bco-precipitation\b',
    r'\bsolid.?state\b',
    r'\bargon atmosphere\b',
]

# Characterization patterns
CHAR_PATTERNS = [
    r'\bXRD\b', r'\bTEM\b', r'\bSEM\b', r'\bXPS\b',
    r'\bRaman\b', r'\bEIS\b', r'\bGITT\b',
    r'\bgalvanostatic cycling\b',
    r'\bcyclic voltammetry\b', r'\bCV\b',
]

def find_spans(text, patterns, label):
    spans = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            spans.append({
                "from_name": "label",
                "to_name": "text",
                "type": "labels",
                "value": {
                    "start": m.start(),
                    "end": m.end(),
                    "text": m.group(),
                    "labels": [label]
                }
            })
    return spans

df = pd.read_csv("annotation/annotation_pool_1000.csv")
tasks = []
total_predictions = 0

for _, row in tqdm(df.iterrows(), total=len(df)):
    sentence = row["sentence"]
    predictions = []

    predictions += find_spans(sentence, MAT_PATTERNS,    "MAT")
    predictions += find_spans(sentence, STRUCT_PATTERNS, "STRUCT")
    predictions += find_spans(sentence, PROP_PATTERNS,   "PROP")
    predictions += find_spans(sentence, SYNTH_PATTERNS,  "SYNTH")
    predictions += find_spans(sentence, CHAR_PATTERNS,   "CHAR")

    total_predictions += len(predictions)

    tasks.append({
        "data": {
            "sentence": sentence,
            "doi": row.get("doi", "")
        },
        "predictions": [{
            "model_version": "rule-based-v1",
            "result": predictions
        }] if predictions else []
    })

Path("annotation").mkdir(exist_ok=True)
with open("annotation/preannotated_1000.json", "w") as f:
    json.dump(tasks, f, indent=2)

covered = sum(1 for t in tasks if t["predictions"])
print(f"\nDone: {len(tasks)} tasks")
print(f"Tasks with predictions: {covered} ({covered/len(tasks)*100:.0f}%)")
print(f"Tasks needing full manual work: {len(tasks) - covered}")
print(f"Total pre-annotated spans: {total_predictions}")