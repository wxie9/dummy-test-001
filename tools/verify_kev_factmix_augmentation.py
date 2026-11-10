#!/usr/bin/env python3
"""Verify a wording-only candidate leaves actual augmentation identical."""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--code-root',type=Path,required=True)
p.add_argument('--original',type=Path,required=True)
p.add_argument('--candidate',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
sys.path.insert(0,str(a.code_root))
from kev.data import load_records,augment,none_pair,source_seed
old=load_records(a.original);new=load_records(a.candidate)
assert len(old)==len(new)==1500
results=[]
for epoch in range(3):
    variants=questions=0
    for x,y in zip(old,new):
        assert x['_meta']['id']==y['_meta']['id']
        def make(r):
            rng=random.Random(source_seed(101,f"{epoch}:{r['_meta']['id']}"))
            vs=[augment(r,rng,p_none=.1,p_none_distract=.12,p_distract=.15)]
            if rng.random()<.25:vs+=none_pair(r,rng)
            return vs
        vx,vy=make(x),make(y)
        assert len(vx)==len(vy)
        for u,v in zip(vx,vy):
            # JSON equality also checks question/option insertion order.
            assert json.dumps(u['questions'])==json.dumps(v['questions'])
            assert u['state']==x['state'] and v['state']==y['state']
            questions+=len(u['questions'])
        variants+=len(vx)
    results.append({'epoch':epoch,'source_contexts':1500,'matching_variants':variants,'matching_questions':questions})
result={'status':'passed','epochs':results,'seed':101,
        'hashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.original,a.candidate,a.code_root/'kev/data.py']},
        'scope':'Actual server augmentation: identical question/option ordering, labels, targets, variants and unchanged record order across three epochs. Replay is unchanged. This verifies supervision equality before tokenization, not identical gradients or effectiveness.'}
a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
