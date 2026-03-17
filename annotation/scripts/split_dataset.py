# annotation/scripts/split_dataset.py
import random
from pathlib import Path

random.seed(42)

def read_conll(path):
    sents, cur = [], []
    for line in Path(path).read_text().splitlines():
        if line.strip(): cur.append(line)
        elif cur: sents.append(cur); cur = []
    if cur: sents.append(cur)
    return sents

def write_conll(sents, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join('\n'.join(s) for s in sents) + '\n')

sents = read_conll('annotation/sib_ner_batch1.conll')
random.shuffle(sents)
n       = len(sents)
n_train = int(n * 0.80)
n_val   = int(n * 0.10)
train = sents[:n_train]
val   = sents[n_train:n_train + n_val]
test  = sents[n_train + n_val:]
write_conll(train, 'data/splits/train.conll')
write_conll(val,   'data/splits/val.conll')
write_conll(test,  'data/splits/test.conll')
print(f'Train: {len(train)}  Val: {len(val)}  Test: {len(test)}')