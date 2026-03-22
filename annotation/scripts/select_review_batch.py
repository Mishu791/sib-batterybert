# scripts/annotation/select_review_batch.py
import json, csv
from pathlib import Path

data = json.loads(Path('annotation/sib_annotated_llm.json').read_text())

# Score each task by number of predicted spans
scored = []
for i, task in enumerate(data):
    spans = task.get('predictions', [{}])[0].get('result', [])
    # Prefer sentences with diverse label types
    labels = set(s['value']['labels'][0] for s in spans)
    score  = len(spans) * 2 + len(labels) * 3   # weight diversity
    scored.append((score, i, task))

scored.sort(reverse=True)
top200 = [task for _, _, task in scored[:200]]

# Save as a new Label Studio import file
out = Path('annotation/review_batch_200.json')
out.write_text(json.dumps(top200, indent=2))

print(f'Selected 200 sentences')
print(f'Avg spans per sentence: {sum(len(t["predictions"][0]["result"]) for t in top200)/200:.1f}')
print(f'Saved -> {out}')