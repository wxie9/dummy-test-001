#!/usr/bin/env python3
"""Assemble 1500 training contexts and a same-generator development diagnostic."""
import json,random,hashlib,sys
from collections import Counter
from pathlib import Path
from build_targeted_v4_components import ROOT,OUT,VERSION,dump,probability,graph
from build_targeted_v4_rules import insufficient,contract
from check_targeted_v4_rules import missing,policy,render,materialize
from check_targeted_v4_numeric import probability as check_prob,graph as check_graph

CHECKS={'probability':check_prob,'multihop':check_graph,'insufficient':missing,'policy':policy}
def digest(s):return hashlib.sha256(' '.join(render(s).casefold().split()).encode()).hexdigest()
def write(path,rows):path.write_text(''.join(dump(r)+'\n' for r in rows))
def main():
    frozen={}
    for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'):
        for line in p.read_text().splitlines():
            r=json.loads(line);frozen[digest(r['state'])]=str(p)
    oldroot=ROOT/'artifacts/kev_training_eval_20261026/targeted_v2_all7_compact'
    parts={};seen=set();new=[]
    for family,check in CHECKS.items():
        for line in (OUT/'components'/f'{family}.candidate.jsonl').read_text().splitlines():
            r=json.loads(line);check(r);materialize(r)
            h=digest(r['state']);assert h not in seen and h not in frozen
            seen.add(h);r['_meta']['split']='train';r['_meta']['id']=r['_meta']['id'].replace('/candidate/','/train/')
            new.append(r)
    assert len(new)==1200
    parts['train']=new
    for split,n in [('train',100),('development',30)]:
        pool=[json.loads(x) for x in (oldroot/(split+'.jsonl')).read_text().splitlines()]
        parts.setdefault(split,[])
        for family in ('tool_routing','temporal','injection'):
            chosen=random.Random(VERSION+split+family).sample([r for r in pool if r['_meta']['family']==family],n)
            for r in chosen:
                h=digest(r['state']);assert h not in seen and h not in frozen;seen.add(h)
            parts[split].extend(chosen)
    # New draws are an in-generator diagnostic, never an untouched-generalization test.
    for family in CHECKS:
        made=0;attempt=0
        while made<60:
            attempt+=1;assert attempt<5000
            rng=random.Random(VERSION+':development:'+family+':'+str(attempt))
            if family=='probability':r=probability(100000+made,['table','bayes','all','any_fail','compare','expected_value'][made%6],rng)
            elif family=='multihop':r=graph(100000+made,['escalation','dependency','ownership'][made%3],rng)
            elif family=='insufficient':r=insufficient(100000+made,['return','approval','tenure','shipping','overtime','warranty','price_match'][made%7],['yes','no','unknown','nondeciding'][(made//7)%4],rng)
            else:r=contract(100000+made,['pay_loss','pay_limit','pay_sublimit','not_purchased','waiting','late','usage','unsafe'][made%8],rng)
            if r is None:continue
            h=digest(r['state'])
            if h in seen or h in frozen:continue
            CHECKS[family](r);materialize(r);seen.add(h)
            r['_meta']['split']='development';r['_meta']['id']=r['_meta']['id'].replace('/candidate/','/development/')
            parts['development'].append(r);made+=1
    files={}
    for split,rows in parts.items():
        random.Random(VERSION+split).shuffle(rows);path=OUT/(split+'.jsonl');write(path,rows)
        files[split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'families':dict(Counter(r['_meta']['family'] for r in rows)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    assert files['train']['contexts']==1500
    manifest={'version':VERSION,'status':'assembled_text_checked_tokenization_pending','files':files,
        'new_four_families':1200,'unchanged_three_families':300,'replay_plan':6000,
        'checks':{'visible_text_recomputed_new_train':1200,'visible_text_recomputed_new_development':240,'kev_materialize':'passed','train_development_exact_overlap':0,'frozen_test_exact_overlap':0},
        'development_scope':'Same authored generators with disjoint draws. Useful for interpolation/overfit diagnosis, not independent semantic generalization.',
        'limitations':['No independent external model/human reviewer.','Hard-v1 errors informed the design.','The same grammar is shared across generated train/dev.','No fresh untouched test result exists yet.'],
        'training_plan':{'epochs':1,'lr':1e-5,'seed':101,'lora':16,'batch':4,'accum':2,'replay':6000,'init':'original pre-targeted stage3','augmentation':'same as v2'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'component_status.json').write_text(json.dumps({'status':'assembled_text_checked_tokenization_pending','manifest':'manifest.json','remaining':['Both tokenizer preflight','Training','Seven-category paired evaluation','Repeated seeds and independent validation if improvements appear']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(files,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
