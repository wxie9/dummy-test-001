#!/usr/bin/env python3
"""Assemble the full 1500-context revision; retain three families byte-for-byte."""
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from build_targeted_v5 import digest
from build_kev_probability_transfer_candidates import verify as probability
from build_kev_multihop_transfer_candidates import verify as multihop
from build_kev_insufficient_transfer_candidates import verify as insufficient
from build_kev_policy_transfer_candidates import verify as policy
from check_targeted_v4_rules import materialize

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OLD=BASE/'targeted_v6_20261030'
OUT=BASE/'targeted_v7_20261030'
RETAINED={'tool_routing','temporal','injection'}
CHECKS={'probability':probability,'multihop':multihop,'insufficient':insufficient,'policy':policy}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (OUT/'run_status.json').exists(),'Do not rebuild a launched experiment'
    OUT.mkdir(exist_ok=True);seen=set();splits={}
    manifest={'version':'targeted-v7-20261030','status':'assembled_local_checks_passed_remote_preflight_pending','goal_achieved':False,'replay_contexts_separate':6000,'files':{},'sources':{},'training_plan':{'epochs':1,'seed':101,'lr':1e-5,'lora':16,'batch':4,'accum':2,'replay':6000,'init':'original pre-targeted stage3'},'limitations':['Different visible contexts are not statistically independent; generators share templates.','The official test has informed diagnostics; subsequent evaluation is not a fresh blind holdout.','Four regenerated families change rules, layouts, options and supervision density together.','Insufficient-information now has one action question per context, compared with five in v6.','Retained three families remain unchanged including known wording ambiguities.','No new model effect has been measured.']}
    for split,expected in [('train',1500),('development',334)]:
        oldlines=(OLD/(split+'.jsonl')).read_text().splitlines();retained={json.loads(l)['_meta']['id']:l for l in oldlines if json.loads(l)['_meta']['family'] in RETAINED}
        rows=[json.loads(l) for l in retained.values()]
        for family,verify in CHECKS.items():
            p=BASE/(family+'_transfer_candidates_20261030')/(split+'.candidate.jsonl');manifest['sources'][str(p.relative_to(BASE))]=sha(p)
            for line in p.read_text().splitlines():
                r=json.loads(line);assert r['_meta']['family']==family;verify(r);parent=r['_meta']['id']
                r['_meta'].update(v7_parent_id=parent,id='targeted-v7-20261030/'+parent,group_id='targeted-v7-20261030/'+r['_meta']['group_id'],source='targeted-v7-20261030/'+family)
                for q in r['questions'].values():q['src']=r['_meta']['source']
                verify(r);rows.append(r)
        assert len(rows)==expected
        hashes=[digest(r['state']) for r in rows];assert len(set(hashes))==len(rows) and not seen.intersection(hashes);seen.update(hashes)
        assert len({r['_meta']['id'] for r in rows})==len(rows)
        for r in rows:materialize(r)
        random.Random('targeted-v7-20261030/'+split).shuffle(rows)
        lines=[retained[r['_meta']['id']] if r['_meta']['family'] in RETAINED else json.dumps(r,ensure_ascii=False,sort_keys=True) for r in rows]
        p=OUT/(split+'.jsonl');p.write_text('\n'.join(lines)+'\n');splits[split]=rows
        assert {json.loads(l)['_meta']['id']:l for l in lines if json.loads(l)['_meta']['family'] in RETAINED}==retained
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'families':dict(Counter(r['_meta']['family'] for r in rows)),'sha256':sha(p),'retained_byte_identical_contexts':len(retained)}
    frozen=set()
    for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'):frozen.update(digest(json.loads(l)['state']) for l in p.read_text().splitlines())
    assert not seen&frozen
    manifest['checks']={'normalized_train_dev_overlap':0,'normalized_frozen_test_overlap':0,'four_replacement_family_visible_label_checks':True,'retained_three_families_byte_identical':True}
    probe=[]
    for family in sorted({r['_meta']['family'] for r in splits['train']}):
        pool=sorted([r for r in splits['train'] if r['_meta']['family']==family],key=lambda r:r['_meta']['id'])
        probe.extend(random.Random('v7-train-probe/'+family).sample(pool,20))
    p=OUT/'train_probe.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in probe));manifest['train_probe']={'contexts':140,'questions':sum(len(r['questions']) for r in probe),'sha256':sha(p)}
    for name in ['launch_qwen3.sh','launch_qwen35.sh','preflight.py','evaluate_development.py']:
        text=(OLD/name).read_text().replace('targeted_v6_20261030','targeted_v7_20261030').replace('targeted-v6','targeted-v7')
        if name=='preflight.py':text=text.replace('len(dev)==336','len(dev)==334')
        (OUT/name).write_text(text)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
