# annotation/scripts/export_conll.py
import json, re, argparse
from pathlib import Path

def tokenize(text):
    return re.findall(r'[A-Za-z0-9_()+\-./]+|[^\s]', text)

def char_offsets(text, tokens):
    offsets, pos = [], 0
    for tok in tokens:
        start = text.find(tok, pos)
        offsets.append((start, start + len(tok)))
        pos = start + len(tok)
    return offsets

def spans_to_bio(text, spans):
    tokens  = tokenize(text)
    offsets = char_offsets(text, tokens)
    labels  = ['O'] * len(tokens)
    for sp in sorted(spans, key=lambda s: s['value']['start']):
        label = sp['value']['labels'][0]
        s, e  = sp['value']['start'], sp['value']['end']
        first = True
        for i, (ts, te) in enumerate(offsets):
            if te > s and ts < e:
                labels[i] = ('B-' if first else 'I-') + label
                first = False
    return list(zip(tokens, labels))

parser = argparse.ArgumentParser()
parser.add_argument('--input',  default='annotation/llm_annotate_checkpoint.json')
parser.add_argument('--output', default='annotation/sib_ner_batch1.conll')
args = parser.parse_args()

data   = json.loads(Path(args.input).read_text())
sents, ents = 0, 0
with open(args.output, 'w') as f:
    for item in data:
        text = item['data']['sentence']
        anns = (item.get('annotations') or item.get('predictions') or [{}])[0].get('result', [])
        pairs = spans_to_bio(text, anns)
        for tok, lbl in pairs:
            f.write(f'{tok} {lbl}\n')
        f.write('\n')
        sents += 1
        ents  += sum(1 for _, l in pairs if l.startswith('B-'))
print(f'Sentences: {sents}  |  Entities: {ents}')
print(f'Saved -> {args.output}')