#!/usr/bin/env python3
"""350-context probability replacement with broad probabilities and magnitudes.

Construction uses authored generators and fixed broad strata, never benchmark
labels. Development shares generators; no independent-generalization claim.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

from build_targeted_v4_components import ROOT, choice, record, percent
from build_targeted_v5 import probability_hard, digest
from check_targeted_v4_numeric import probability as check_probability
from check_targeted_v4_rules import materialize, gold

OUT=ROOT/'artifacts/kev_training_eval_20261026/probability_coverage_candidates_20261030'
VERSION='probability-coverage-candidate-20261030'
BOUNDS=[0,10,30,50,70,90,100]
PROFILES=[(1,5),(1,20),(15,45),(40,75),(70,95),(92,99),(97,99),(1,99)]
COUNTS={'train':{'table':75,'bayes':60,'all':40,'any_fail':50,'any':25,'compare':40,'expected_value':60},
        'development':{'table':10,'bayes':10,'all':8,'any_fail':10,'any':6,'compare':6,'expected_value':10}}


def bucket(p):
    return next(i for i,(l,u) in enumerate(zip(BOUNDS,BOUNDS[1:])) if l<=100*p<u or u==100 and p==1)


def probability_of(ps,kind):
    prod=F(1);none=F(1)
    for p in ps:prod*=p;none*=1-p
    return {'all':prod,'any_fail':1-prod,'any':1-none}[kind]


def independent(i,kind,rng):
    target=i%6
    for _ in range(10000):
        lo,hi=rng.choice(PROFILES)
        values=[rng.randint(lo,hi) for _ in range(rng.randint(2,5))]
        ps=[F(v,100) for v in values];p=probability_of(ps,kind)
        if bucket(p)==target:break
    else:raise AssertionError('Unable to fill probability stratum')
    noun=rng.choice(['delivery routes','processing jobs','backup links','inspection stations'])
    state=f'The following {noun} have mutually independent success events. Their success rates are '+', '.join(f'{v}%' for v in values)+'. These are all the components in the system.'
    prompt={'all':'What is the probability every component succeeds?',
            'any_fail':'What is the probability at least one component fails?',
            'any':'What is the probability at least one component succeeds?'}[kind]
    alternatives=[1-p]+[probability_of(ps,k) for k in ['all','any','any_fail']]+[min(ps),max(ps),sum(ps)/len(ps)]
    alternatives += [max(F(0),p-F(3,1000)),min(F(1),p+F(17,1000)),max(F(0),p-F(29,1000))]
    wrong=list(dict.fromkeys(percent(v) for v in alternatives if percent(v)!=percent(p)))
    rng.shuffle(wrong);assert len(wrong)>=4
    qs={'probability':choice(rng,prompt+' Round to two decimal places.',percent(p),wrong[:4]),
        'bucket':{'type':'score','instructions':prompt+' Select the interval containing the exact probability; [ includes a boundary and ) excludes it.',
                  'criteria':[f'[{l}%, {u}%'+(']' if u==100 else ')') for l,u in zip(BOUNDS,BOUNDS[1:])],
                  'label':bucket(p),'src':VERSION}}
    return record('probability',i,state,qs,{'probabilities':values,'exact_probability':str(p),'stratum':target},kind,
                  '独立事件按乘积及补集计算；概率区间按精确分数确定。')


def rescale(r,scale):
    kind=r['_meta']['subtype'];facts=r['_meta']['facts']
    if kind=='table':
        r['state']=re.sub(r'\b\d+\b',lambda m:str(int(m[0])*scale),r['state'])
        facts['counts']=[x*scale for x in facts['counts']]
    elif kind=='expected_value':
        def money(text):
            return re.sub(r'\$([0-9]+\.[0-9]{2})',lambda m:'$'+f'{Decimal(m[1])*scale:.2f}',text)
        r['state']=money(r['state'])
        for q in r['questions'].values():
            q['criteria']={k:money(v) for k,v in q['criteria'].items()}
        for p in facts['projects'].values():
            p['cost']*=scale;p['values']=[v*scale for v in p['values']]
    facts['scale']=scale
    r['_meta']['review_zh']=f'所有相关计数或金额同乘{scale}；条件概率不变，期望净值同倍缩放。'
    return r


def make(i,kind,rng):
    if kind in ['all','any','any_fail']:return independent(i,kind,rng)
    if kind=='bayes':
        for _ in range(10000):
            r=probability_hard(i,kind,rng);f=r['_meta']['facts']
            p=F(f['prevalence']*f['sensitivity'],f['prevalence']*f['sensitivity']+(100-f['prevalence'])*f['false_positive'])
            if bucket(p)==i%6:return r
        raise AssertionError('Unable to fill posterior stratum')
    r=probability_hard(i,kind,rng)
    if r is None:return None
    if kind=='table':return rescale(r,[1,10,100,1000,10000][i%5])
    if kind=='expected_value':return rescale(r,[1,10,100,1000,10000][i%5])
    return r


def verify(r):
    check_probability(r)
    if r['_meta']['subtype'] in ['all','any','any_fail']:
        # Parse the visible success rates independently of stored latent facts.
        ps=[F(v,100) for v in map(int,re.findall(r'(\d+)%',r['state']))]
        q=r['questions']['probability']['instructions']
        prod=F(1);none=F(1)
        for p in ps:prod*=p;none*=1-p
        expected=1-prod if 'fails' in q else 1-none if 'at least one' in q else prod
        assert gold(r,'probability')==percent(expected)
        assert r['questions']['bucket']['label']==bucket(expected)
    materialize(r)


def coverage(rows):
    bins=defaultdict(Counter);scales=defaultdict(Counter);magnitudes=[]
    for r in rows:
        kind=r['_meta']['subtype'];f=r['_meta']['facts']
        if kind in ['all','any','any_fail']:
            bins[kind][bucket(probability_of([F(v,100) for v in f['probabilities']],kind))]+=1
        if kind=='bayes':
            p=F(f['prevalence']*f['sensitivity'],f['prevalence']*f['sensitivity']+(100-f['prevalence'])*f['false_positive'])
            bins[kind][bucket(p)]+=1
        if 'scale' in f:scales[kind][f['scale']]+=1
        if kind=='expected_value':magnitudes.extend(abs(v) for p in f['projects'].values() for v in p['values'])
    return {'probability_bins':dict(bins),'numeric_scale_factors':dict(scales),
            'absolute_payoff_range':[min(magnitudes),max(magnitudes)]}


def main():
    OUT.mkdir(exist_ok=True)
    # Only text fingerprints are used from benchmark files, to exclude overlap.
    frozen={digest(json.loads(l)['state']) for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl') for l in p.read_text().splitlines()}
    seen=set();manifest={'status':'candidate_only_not_in_training','scope':'350-context replacement component, not additional contexts or a full seven-family corpus. Fixed broad probability strata and five magnitude factors; no benchmark labels used in construction. Development uses the same generators.',
        'probability_bin_boundaries_pct':BOUNDS,'files':{}}
    for split,counts in COUNTS.items():
        rows=[]
        for kind,n in counts.items():
            for i in range(n):
                for attempt in range(10000):
                    r=make(i,kind,random.Random(f'{VERSION}/{split}/{kind}/{i}/{attempt}'))
                    if r is not None and digest(r['state']) not in seen|frozen:break
                else:raise AssertionError('No unique context found')
                h=digest(r['state']);seen.add(h);m=r['_meta'];m.update(id=f'{VERSION}/{split}/{kind}/{i}',group_id=f'{VERSION}/{split}/{kind}/{i}',source=VERSION,split=split,text_sha256=h)
                for q in r['questions'].values():q['src']=VERSION
                verify(r);rows.append(r)
        mutations=0
        for r in rows:
            for name,q in r['questions'].items():
                bad=copy.deepcopy(r);b=bad['questions'][name]
                b['label']=not b['label'] if b['type']=='noul' else (b['label']+1)%len(b['criteria']) if b['type']=='score' else next(k for k in b['criteria'] if k!=b['label'])
                try:verify(bad)
                except AssertionError:mutations+=1
                else:raise AssertionError(('Bad label accepted',name,r['_meta']['id']))
        random.Random(VERSION+split).shuffle(rows)
        path=OUT/(split+'.candidate.jsonl');path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'wrong_label_mutations_rejected':mutations,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'coverage':coverage(rows)}
    manifest['checks']={'exact_state_train_dev_overlap':0,'exact_state_frozen_test_overlap':0,'all_visible_numeric_labels_recomputed':True}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
