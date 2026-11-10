#!/usr/bin/env python3
"""Mix the three-family error-neighborhood data with frozen v6 rows for the other four families."""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path('/Users/chen/Documents/ChatGPT/procogs')
BASE = ROOT / 'artifacts/kev_training_eval_20261026'
THREE = BASE / 'targeted_three_error_neighborhood_20261031'
V6 = BASE / 'targeted_v6_20261030'
OUT = BASE / 'targeted_all7_error_neighborhood_mix_20261031'
KEEP = {'tool_routing', 'insufficient', 'policy', 'injection'}
SEED = 101

def read(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(split):
    three = read(THREE / f'{split}.jsonl')
    four_all = read(V6 / f'{split}.jsonl')
    four = [r for r in four_all if r['_meta']['family'] in KEEP]
    assert len(four) == (780 if split == 'train' else 190)
    rows = three + four
    random.Random(SEED + (0 if split == 'train' else 1)).shuffle(rows)
    path = OUT / f'{split}.jsonl'
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in rows))
    return path, rows, len(three), len(four)

OUT.mkdir(parents=True, exist_ok=True)
files = {}
for split in ('train', 'development'):
    path, rows, n3, n4 = write(split)
    fam = Counter(r['_meta']['family'] for r in rows)
    qs = Counter()
    for r in rows: qs[r['_meta']['family']] += len(r['questions'])
    files[split] = {'records':len(rows), 'questions':sum(qs.values()),
                    'records_by_family':dict(sorted(fam.items())),
                    'questions_by_family':dict(sorted(qs.items())),
                    'three_family_records':n3, 'frozen_v6_four_family_records':n4,
                    'sha256':sha(path)}

manifest = {
  'version':'targeted-all7-error-neighborhood-mix-20261031',
  'status':'assembled_local_checks_pending',
  'seed':SEED,
  'init':'original qwen3.5 replica-20261026/stage3; do not continue from a targeted stage4',
  'method':'three-family hard-v1 error-neighborhood data plus byte-semantic-identical frozen v6 rows for tool_routing, insufficient, policy, injection',
  'training':{'epochs':1,'lr':1e-5,'lora_rank':16,'batch':4,'accum':2,'replay':0},
  'files':files,
  'source_sha256':{
    'three_train':sha(THREE/'train.jsonl'),'three_development':sha(THREE/'development.jsonl'),
    'v6_train':sha(V6/'train.jsonl'),'v6_development':sha(V6/'development.jsonl')},
  'evidence_boundary':['hard-v1 test errors were used to design three-family training rows, so hard-v1 is a targeted repair backtest, not blind evaluation.',
                       'development rows share generators or seed semantic skeletons with training and measure local transfer only.']}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
