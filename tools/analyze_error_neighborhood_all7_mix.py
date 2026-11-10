#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path('/Users/chen/Documents/ChatGPT/procogs')
ART=ROOT/'artifacts/kev_training_eval_20261026'
BASE=ART/'targeted_v6_20261030/evidence/runs/replica-20261026/benchmarks'
RUN=ART/'targeted_all7_error_neighborhood_mix_20261031/evidence/qwen35-20261031-targeted-all7-error-neighborhood-mix-e1'
THREE=ART/'targeted_three_error_neighborhood_20261031/evidence/qwen35-20261031-targeted-three-error-neighborhood-e1/eval-hard-v1/rows.json'
OUT=ART/'targeted_all7_error_neighborhood_mix_20261031/comparison.json'

FAMILIES={
 '工具路由':('devtools','when2call','action'),
 '时间与数值':('hard','hard_temporal_numeric',None),
 '概率':('hard','hard_probability',None),
 '信息不足':('hard','hard_ambiguous',None),
 '多跳推理':('hard','hard_multi_hop',None),
 '长政策':('hard','hard_long_policy',None),
 '提示注入':('devtools','prompt_injection','injection'),
}

def load(p): return json.loads(Path(p).read_text())
def key(r): return (r['id'],r['question'])
def ok(r): return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']
def tally(before,after,keys):
 b=[ok(before[k]) for k in keys]; a=[ok(after[k]) for k in keys]
 repaired=sum(not x and y for x,y in zip(b,a)); broken=sum(x and not y for x,y in zip(b,a))
 return {'n':len(keys),'before_correct':sum(b),'after_correct':sum(a),
  'before_acc':round(100*sum(b)/len(b),2),'after_acc':round(100*sum(a)/len(a),2),
  'delta_correct':sum(a)-sum(b),'delta_pp':round(100*(sum(a)-sum(b))/len(b),2),
  'original_errors':len(b)-sum(b),'repaired':repaired,'newly_broken':broken}

def tally_rows(before_rows,after_rows):
 assert len(before_rows)==len(after_rows)
 # Benchmark serialization order is stable. This preserves a known duplicate
 # devtools id/question pair which cannot be keyed without losing one row.
 b=[ok(r) for r in before_rows]; a=[ok(r) for r in after_rows]
 repaired=sum(not x and y for x,y in zip(b,a)); broken=sum(x and not y for x,y in zip(b,a))
 return {'n':len(b),'before_correct':sum(b),'after_correct':sum(a),
  'before_acc':round(100*sum(b)/len(b),2),'after_acc':round(100*sum(a)/len(a),2),
  'delta_correct':sum(a)-sum(b),'delta_pp':round(100*(sum(a)-sum(b))/len(b),2),
  'original_errors':len(b)-sum(b),'repaired':repaired,'newly_broken':broken}

base_rows={'hard':load(BASE/'hard-v1-test/rows.json'),'devtools':load(BASE/'devtools-v1-test/rows.json')}
post_rows={'hard':load(RUN/'eval-hard-v1/rows.json'),'devtools':load(RUN/'eval-devtools-v1/rows.json')}
base={s:{key(r):r for r in rows} for s,rows in base_rows.items()}
post={s:{key(r):r for r in rows} for s,rows in post_rows.items()}
families={}; target=[]
for name,(suite,source,question) in FAMILIES.items():
 keys=[k for k,r in base[suite].items() if r['source']==source and (question is None or r['question']==question)]
 families[name]=tally(base[suite],post[suite],keys)
 target += [(suite,k) for k in keys]

def tally_cross(pairs):
 b=[ok(base[s][k]) for s,k in pairs]; a=[ok(post[s][k]) for s,k in pairs]
 return {'n':len(pairs),'before_correct':sum(b),'after_correct':sum(a),'before_acc':round(100*sum(b)/len(b),2),
  'after_acc':round(100*sum(a)/len(a),2),'delta_correct':sum(a)-sum(b),
  'delta_pp':round(100*(sum(a)-sum(b))/len(b),2),'repaired':sum(not x and y for x,y in zip(b,a)),
  'newly_broken':sum(x and not y for x,y in zip(b,a))}

# Development pairing and per-family grouping from source dataset metadata.
db={key(r):r for r in load(RUN/'development-before/rows.json')}; da={key(r):r for r in load(RUN/'development-after/rows.json')}
dev_groups=defaultdict(list)
id_family={}
for split in ['development']:
 for line in (ART/'targeted_all7_error_neighborhood_mix_20261031'/f'{split}.jsonl').read_text().splitlines():
  r=json.loads(line); id_family[r['_meta']['id']]=r['_meta']['family']
for k in db: dev_groups[id_family[k[0]]].append(k)
dev={f:tally(db,da,ks) for f,ks in sorted(dev_groups.items())}

# Direct three-only comparison on the same three hard families.
three={key(r):r for r in load(THREE)}
three_compare={}
for name in ['时间与数值','概率','多跳推理']:
 suite,source,question=FAMILIES[name]
 keys=[k for k,r in base[suite].items() if r['source']==source]
 three_compare[name]={
  'three_only_correct':sum(ok(three[k]) for k in keys),
  'all7_mix_correct':sum(ok(post[suite][k]) for k in keys),
  'difference_all7_minus_three_only':sum(ok(post[suite][k])-ok(three[k]) for k in keys)}

result={'run':'qwen35-20261031-targeted-all7-error-neighborhood-mix-e1',
 'families':families,'seven_target_total':tally_cross(target),
 'hard_v1_all':tally_rows(base_rows['hard'],post_rows['hard']),
 'devtools_v1_all':tally_rows(base_rows['devtools'],post_rows['devtools']),
 'mixed_development':dev,'three_family_vs_three_only':three_compare,
 'limits':['hard-v1 errors were used to design three-family training data; hard-v1 is a targeted repair backtest.','One seed; development shares generators or semantic skeletons with training.']}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
