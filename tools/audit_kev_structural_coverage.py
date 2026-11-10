#!/usr/bin/env python3
"""Inspect coverage, preserving fixed test occurrences and avoiding causal claims."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
V6=BASE/'targeted_v6_20261030'
THREE=BASE/'targeted_v6_3ep_20261030'
OUT=BASE/'structural_coverage_audit_20261030'

def read(path):return [json.loads(line) for line in path.read_text().splitlines()]
def text(state):
    if isinstance(state,str):return state
    if isinstance(state,dict):return '\n'.join(text(x) for x in state.values())
    return '\n'.join(text(x) for x in state)
def ok(r):return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']
def desc(values):
    values=sorted(values)
    return {k:values[round((len(values)-1)*p)] for k,p in [('min',0),('p25',.25),('median',.5),('p75',.75),('max',1)]}

def main():
    OUT.mkdir(exist_ok=True)
    trainpath=V6/'train.jsonl';testpath=V6/'evidence/evals/hard-v1/test.jsonl'
    train=read(trainpath);test=read(testpath)
    source={'probability':'hard_probability','multihop':'hard_multi_hop','insufficient':'hard_ambiguous','policy':'hard_long_policy'}
    out={'scope':'Coverage observations on generated training data and already inspected diagnostic tests; neither causal attribution nor independent generalization evidence.',
         'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [trainpath,testpath]},'families':{}}
    for family,src in source.items():
        a=[r for r in train if r['_meta']['family']==family];b=[r for r in test if r['_meta']['source']==src]
        axes={'training_contexts':len(a),'test_contexts':len(b),'training_subtypes':dict(Counter(r['_meta']['subtype'] for r in a)),
              'test_subtypes':dict(Counter(r['_meta']['subtype'] for r in b)),
              'training_state_chars':desc([len(text(r['state'])) for r in a]),'test_state_chars':desc([len(text(r['state'])) for r in b]),
              'test_templates':dict(Counter(r['_meta']['template'] for r in b))}
        if family=='policy':
            axes['training_domains']=dict(Counter(r['_meta']['facts']['domain'] for r in a))
            axes['test_domains']=dict(Counter(r['_meta']['facts']['domain'] for r in b))
        out['families'][family]=axes
    table_train=[r for r in train if r['_meta']['family']=='probability' and r['_meta']['subtype']=='table']
    pairs=[('North depot','South depot'),('Supplier R','Supplier S'),('Morning shift','Evening shift'),('Coastal branch','Inland branch')]
    tpositions=Counter()
    for r in table_train:
        target=re.search(r'origin is (.+?)\?',r['questions']['reverse']['instructions'])[1]
        labels=next(p for p in pairs if target in p)
        positions=[text(r['state']).find(name) for name in labels];assert min(positions)>=0
        tpositions[sorted(labels,key=lambda name:text(r['state']).find(name)).index(target)]+=1
    table_test=[r for r in test if r['_meta']['source']=='hard_probability' and r['_meta']['subtype']=='table']
    testmeta={};examples=[]
    for r in table_test:
        f=r['_meta']['facts'];labels=list(f['counts']);s=text(r['state'])
        positions={name:s.find(name+':') for name in labels};assert len(labels)==2 and min(positions.values())>=0
        pos=sorted(labels,key=positions.get).index(f['row'])
        testmeta[r['_meta']['id']]={'target_row_position':pos,'direction':f['ask'],'template':r['_meta']['template']}
        examples.append({'id':r['_meta']['id'],**testmeta[r['_meta']['id']]})
    out['probability_table']={'training_target_row_positions':dict(tpositions),'test_target_row_positions':dict(Counter(x['target_row_position'] for x in testmeta.values())),
        'test_cases':examples,'evaluation':{}}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        paths=[THREE/'evidence/runs'/original/'benchmarks/hard-v1-test/rows.json',V6/'evidence/runs'/(model+'-20261030-targeted-v6')/'eval-hard-v1/rows.json',THREE/'evidence/runs'/(model+'-20261030-targeted-v6-3ep')/'eval-hard-v1/rows.json']
        tables=[json.loads(p.read_text()) for p in paths]
        for p in paths:out['files'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        signature=lambda rs:[(r['id'],r['question'],r['keys'],r['label'],r['source']) for r in rs]
        assert signature(tables[0])==signature(tables[1])==signature(tables[2])
        groups=defaultdict(lambda:[0,0,0,0])
        for a,b,c in zip(*tables):
            if a['id'] not in testmeta:continue
            m=testmeta[a['id']]
            for key in [m['direction']+'/row_'+str(m['target_row_position']),'all/row_'+str(m['target_row_position'])]:
                v=groups[key];v[3]+=1
                for i,r in enumerate([a,b,c]):v[i]+=int(ok(r))
        out['probability_table']['evaluation'][model]={k:dict(zip(['stage3','v6_one_epoch','v6_three_epochs','questions'],v)) for k,v in sorted(groups.items())}
    (OUT/'coverage.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'table':out['probability_table'],'policy':out['families']['policy'],'lengths':{k:{z:v[z] for z in ['training_state_chars','test_state_chars']} for k,v in out['families'].items()}},ensure_ascii=False))

if __name__=='__main__':main()
