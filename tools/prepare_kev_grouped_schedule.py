#!/usr/bin/env python3
"""Prepare a scheduler-only control against completed v9; do not launch it."""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from kev_matched_sampling import load_pair_membership,shuffle_matched_requests

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
SOURCE=BASE/'targeted_v9_matched_20261030'
OUT=BASE/'v9_grouped_schedule_candidate_20261030'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'launch.json').exists()
    data=[json.loads(l) for l in (SOURCE/'train.jsonl').read_text().splitlines()]
    slots=data+[{'_meta':{'id':'replay-slot/'+str(i)}} for i in range(6000)]
    members=load_pair_membership(SOURCE/'pair_mapping.json',slots)
    audits=[]
    for seed in [0,1,7,42,101,20261030]:
        rows=list(slots);rng=random.Random(seed)
        for epoch in range(3):
            shuffle_matched_requests(rows,members,rng,4)
            assert Counter(map(id,rows))==Counter(map(id,slots))
            positions={r['_meta']['id']:i for i,r in enumerate(rows)}
            pairs=json.loads((SOURCE/'pair_mapping.json').read_text())['train']
            same=sum(positions[p['base_id']]//4==positions[p['matched_id']]//4 for p in pairs)
            assert same==1020 and len(rows)==8520
            audits.append({'seed':seed,'epoch':epoch,'records':len(rows),'matched_pairs_same_microbatch':same,'optimizer_steps':(len(rows)+7)//8,'slot_order_sha256':hashlib.sha256(json.dumps([r['_meta']['id'] for r in rows]).encode()).hexdigest()})
    original=SOURCE/'evidence/stages/stage3/kev/train.py';code=original.read_text()
    assert code.count('        rng.shuffle(reqs)')==1
    # Import inside the existing package so all model/evaluation code is unchanged.
    anchor='from collections import Counter\n';assert anchor in code
    code=code.replace(anchor,anchor+'from .matched_sampling import load_pair_membership, shuffle_matched_requests\n')
    # parse_args uses argparse.ArgumentParser; add one opt-in control flag.
    anchor='    ap = argparse.ArgumentParser()\n';assert anchor in code
    code=code.replace(anchor,anchor+'    ap.add_argument("--matched_pairs", default="", help="Explicit train pair mapping; keep paired views in one microbatch")\n')
    anchor='    for ep in range(a.epochs):\n';assert code.count(anchor)==1
    code=code.replace(anchor,'    pair_membership = load_pair_membership(a.matched_pairs, reqs)\n'+anchor)
    code=code.replace('        rng.shuffle(reqs)','        if pair_membership:\n            shuffle_matched_requests(reqs, pair_membership, rng, a.batch)\n        else:\n            rng.shuffle(reqs)')
    (OUT/'train.py').write_text(code)
    (OUT/'matched_sampling.py').write_bytes((ROOT/'tools/kev_matched_sampling.py').read_bytes())
    import ast
    ast.parse(code);ast.parse((OUT/'matched_sampling.py').read_text())
    manifest={'status':'sampler_verified_not_launched','goal_achieved':False,'data_source':str(SOURCE),'data_sha256':sha(SOURCE/'train.jsonl'),'base_contexts':1500,'additional_views':1020,'replay':6000,'expected_steps':1065,'original_train_code_sha256':sha(original),'modified_train_code_sha256':sha(OUT/'train.py'),'sampler_sha256':sha(OUT/'matched_sampling.py'),'change':'Only training record schedule: matched pairs co-occur within a microbatch. CE, model architecture, original-stage3 initialization and data contents remain fixed. No explicit contrastive loss.','validation':audits,'limitations':['Record grouping changes stochastic gradients and per-record augmentation normalization through batch composition. This is not proof that grouping fixes performance.','Replay slots suffice for schedule verification because shuffling uses positions; actual replay identities and full preflight remain required before launch.','This is a prepared candidate only; no new model training or results exist.','The three retained categories are not edited, including ambiguous date wording.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':manifest['status'],'audited_schedules':len(audits),'pairs_per_schedule':1020,'records':8520,'source_sha256':manifest['data_sha256']}))


if __name__=='__main__':main()
