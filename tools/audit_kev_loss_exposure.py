#!/usr/bin/env python3
"""Measure scalar CE coefficients from exact batching/augmentation, no inference.

This is exposure accounting, not a gradient-norm or causal performance claim.
The counterfactual gives each source record equal weight inside an accumulation
group and divides that record's weight across its variants and questions.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--code-root',type=Path,required=True)
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--suite',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    sys.path.insert(0,str(args.code_root))
    from kev.data import load_records, augment, none_pair, source_seed
    from kev.suite import load_split
    from kev.train import accumulation_records
    targeted=load_records(args.data)
    pool=load_split(args.suite,'train')
    replay=random.Random('replay:101').sample(pool,6000)
    reqs=targeted+replay
    assert targeted and len(replay)==6000 and len(reqs)==len(targeted)+6000
    expected_steps=math.ceil(len(reqs)/8)
    target_ids={r['_meta']['id'] for r in targeted}
    assert len(target_ids)==len(targeted)
    shuffle=random.Random(101)
    results=[]
    for epoch in range(3):
        shuffle.shuffle(reqs)
        by_family=defaultdict(Counter)
        by_question=defaultdict(Counter)
        by_subtype=defaultdict(Counter)
        none_label_mass=defaultdict(Counter)
        def category(r):
            return r['_meta']['family'] if r['_meta']['id'] in target_ids else 'replay'
        for mb in range(math.ceil(len(reqs)/4)):
            chunk=reqs[mb*4:(mb+1)*4]
            records=[]
            for r in chunk:
                rng=random.Random(source_seed(101,f"{epoch}:{r['_meta']['id']}"))
                variants=[augment(r,rng,p_none=.1,p_none_distract=.12,p_distract=.15)]
                if rng.random()<.25:variants+=none_pair(r,rng)
                records.append((r,variants))
            nv=sum(len(vs) for _,vs in records)
            group_records=accumulation_records(len(reqs),4,2,mb)
            actual_divisor=group_records*(nv/len(chunk))
            for r,variants in records:
                family=category(r);sub=r['_meta'].get('subtype','unspecified')
                for table,key in [(by_family,family),(by_subtype,family+'/'+sub)]:
                    table[key]['contexts']+=1
                    table[key]['variants']+=len(variants)
                    table[key]['actual_ce_mass']+=len(variants)/actual_divisor
                    table[key]['equal_record_ce_mass']+=1/group_records
                    table[key]['none_pair_records']+=len(variants)>1
                for var in variants:
                    nq=len(var['questions'])
                    for qid,q in var['questions'].items():
                        key=family+'/'+qid
                        actual=1/(actual_divisor*nq)
                        equal=1/(group_records*len(variants)*nq)
                        by_question[key]['question_occurrences']+=1
                        by_question[key]['actual_ce_mass']+=actual
                        by_question[key]['equal_record_ce_mass']+=equal
                        if family=='insufficient':
                            # Record raw labels; do not merge "none of the options"
                            # with "facts insufficient" or assign semantic synonyms.
                            label=q['criteria'][q['label']] if q['type']=='choice' else str(q['label'])
                            label=str(label)
                            none_label_mass[qid+'/'+label]['actual_ce_mass']+=actual
                            none_label_mass[qid+'/'+label]['occurrences']+=1
        total_actual=sum(v['actual_ce_mass'] for v in by_family.values())
        total_equal=sum(v['equal_record_ce_mass'] for v in by_family.values())
        assert abs(total_actual-expected_steps)<1e-8 and abs(total_equal-expected_steps)<1e-8
        for table in [by_family,by_subtype,by_question]:
            for v in table.values():
                v['actual_share_pct']=100*v['actual_ce_mass']/total_actual
                v['actual_over_equal_record']=v['actual_ce_mass']/v['equal_record_ce_mass']
        results.append({'epoch':epoch,'total_ce_mass':total_actual,'families':dict(by_family),
            'subtypes':dict(by_subtype),'questions':dict(by_question),'insufficient_raw_label_exposure':dict(none_label_mass)})
    result={'data_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest(),
        'code_hashes':{n:hashlib.sha256((args.code_root/'kev'/n).read_bytes()).hexdigest() for n in ['train.py','data.py']},
        'targeted_contexts':len(targeted),'replay_contexts':6000,'seed':101,'batch':4,'accum':2,'epochs':results,
        'scope':'Exact scalar coefficients before optimizer, clipping, learning-rate scaling and gradient direction. Input counts refer to records, not independent base cases when matched views exist. Requires a separate preflight to confirm no input filtering. Three simulated epoch seeds are audited even for one-epoch training; only epoch 0 then describes actual exposure. Does not prove these weights caused benchmark regressions.',
        'toy_example':{'source_record_variant_counts':[3,1,1,1],'group_records':8,
            'actual_source_coefficients':[3/12,1/12,1/12,1/12],
            'equal_record_source_coefficients':[1/8]*4,
            'within_batch_ratio_three_variants_vs_one':3}}
    args.out.parent.mkdir(exist_ok=True,parents=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'data_sha256':result['data_sha256'],'epochs':[{'epoch':r['epoch'],'families':r['families']} for r in results]},ensure_ascii=False))


if __name__=='__main__':main()
