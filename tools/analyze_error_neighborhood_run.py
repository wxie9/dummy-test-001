#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/chen/Documents/ChatGPT/procogs')
BASE = ROOT/'artifacts/kev_training_eval_20261026/targeted_v6_20261030/evidence/runs/replica-20261026/benchmarks/hard-v1-test/rows.json'
RUN = ROOT/'artifacts/kev_training_eval_20261026/targeted_three_error_neighborhood_20261031/evidence/qwen35-20261031-targeted-three-error-neighborhood-e1'
POST = RUN/'eval-hard-v1/rows.json'
SOURCE = ROOT/'third_party/kev-source-20261025/evals/hard-v1/test.jsonl'
OUT = ROOT/'artifacts/kev_training_eval_20261026/targeted_three_error_neighborhood_20261031/comparison.json'

NAMES = {'hard_temporal_numeric':'时间与数值','hard_probability':'概率','hard_multi_hop':'多跳推理'}

def correct(r): return max(range(len(r['p'])), key=r['p'].__getitem__) == r['label']
def key(r): return (r['id'], r['question'])

before_rows = json.loads(BASE.read_text())
after_rows = json.loads(POST.read_text())
before, after = ({key(r):r for r in rows} for rows in (before_rows,after_rows))
meta = {r['_meta']['id']:r['_meta'] for r in map(json.loads,SOURCE.read_text().splitlines())}

def tally(keys):
    b=[correct(before[k]) for k in keys]; a=[correct(after[k]) for k in keys]
    repaired=sum((not x) and y for x,y in zip(b,a)); broken=sum(x and (not y) for x,y in zip(b,a))
    return {'n':len(keys),'before_correct':sum(b),'after_correct':sum(a),
            'before_acc':round(sum(b)/len(b)*100,2),'after_acc':round(sum(a)/len(a)*100,2),
            'delta_correct':sum(a)-sum(b),'delta_pp':round((sum(a)-sum(b))/len(b)*100,2),
            'original_errors':len(b)-sum(b),'repaired':repaired,
            'repair_rate':round(repaired/(len(b)-sum(b))*100,2) if len(b)>sum(b) else None,
            'original_correct':sum(b),'newly_broken':broken,
            'break_rate':round(broken/sum(b)*100,2) if sum(b) else None}

families={}
target=[]
for source,name in NAMES.items():
    keys=[k for k,r in before.items() if r['source']==source]
    target += keys
    sub=defaultdict(list)
    for k in keys: sub[meta[k[0]].get('subtype','unknown')].append(k)
    families[name] = tally(keys) | {'subtypes':{s:tally(ks) for s,ks in sorted(sub.items())}}

dev_before=json.loads((RUN/'development-before/rows.json').read_text())
dev_after=json.loads((RUN/'development-after/rows.json').read_text())
db={key(r):r for r in dev_before}; da={key(r):r for r in dev_after}; dkeys=list(db)
dev_b=sum(correct(db[k]) for k in dkeys); dev_a=sum(correct(da[k]) for k in dkeys)

result={
  'run':'qwen35-20261031-targeted-three-error-neighborhood-e1',
  'hard_v1_all':tally(list(before)),
  'hard_v1_target_three':tally(target),
  'families':families,
  'heldout_neighborhood_dev':{'n':len(dkeys),'before_correct':dev_b,'after_correct':dev_a,
    'before_acc':round(dev_b/len(dkeys)*100,2),'after_acc':round(dev_a/len(dkeys)*100,2),
    'delta_correct':dev_a-dev_b,'delta_pp':round((dev_a-dev_b)/len(dkeys)*100,2)},
  'interpretation_limits':['训练样本由 hard-v1 原始错题的上下文定向变换得到，因此 hard-v1 不再是盲测。','heldout neighborhood 与训练变体不同，但共享原错题语义骨架；它衡量局部变体迁移，不等同于独立分布泛化。']
}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
