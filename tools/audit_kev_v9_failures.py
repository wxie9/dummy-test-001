#!/usr/bin/env python3
"""Audit official payment errors and exact matched-pair training proximity."""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args();p=a.directory;e=p/'evidence'
    raw={r['_meta']['id']:r for r in map(json.loads,(e/'evals/hard-v1/test.jsonl').read_text().splitlines()) if r['_meta']['source']=='hard_long_policy'}
    money=lambda s:float(s.replace('$','').replace(',',''))
    result={'scope':'Already-inspected official diagnostic cases; descriptive, not a causal or blind-generalization claim.','models':{},'hashes':{}}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        result['models'][model]={}
        for phase,path in [('before',e/'runs'/original/'benchmarks/hard-v1-test/rows.json'),('after',e/'runs'/(model+'-20261030-targeted-v9-matched')/'eval-hard-v1/rows.json')]:
            result['hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest();observed=defaultdict(dict)
            for row in json.loads(path.read_text()):
                if row['id'] not in raw:continue
                q=raw[row['id']]['questions'][row['question']]
                assert row['keys'][row['label']]==q['label'] and set(row['keys'])==set(q['criteria'])
                assert row['question'] not in observed[row['id']]
                key=row['keys'][max(range(len(row['p'])),key=row['p'].__getitem__)]
                observed[row['id']][row['question']]=q['criteria'][key]
            counts=defaultdict(Counter);examples=[]
            for rid,r in raw.items():
                q=r['questions']['amount'];gold=money(q['criteria'][q['label']]);answers=observed[rid];assert set(answers)=={'amount','outcome'}
                offered=any(money(v)==0 for v in q['criteria'].values());amount=money(answers['amount']);pred_pay=answers['outcome'].startswith('Pay ')
                k=('positive' if gold>0 else 'zero')+'/zero_offered='+str(offered);s=counts[k]
                s['contexts']+=1;s['correct_amount']+=amount==gold;s['predicted_zero']+=amount==0
                s['pay_reason_and_zero_amount']+=pred_pay and amount==0
                if gold>0 and amount!=gold:examples.append({'id':rid,'gold':gold,'predicted':amount,'zero_offered':offered,'predicted_outcome':answers['outcome']})
            result['models'][model][phase]={'strata':dict(counts),'positive_amount_errors':examples}
    (p/'real_policy_zero_preference_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    rows=[json.loads(l) for l in (p/'train.jsonl').read_text().splitlines()]
    ids=[r['_meta']['id'] for r in rows]+['replay-slot/'+str(i) for i in range(6000)]
    # random.shuffle depends on the slot count/order, not replay slot contents.
    random.Random(101).shuffle(ids);positions={rid:i for i,rid in enumerate(ids)}
    groups=defaultdict(Counter);distances=[]
    pairs=json.loads((p/'pair_mapping.json').read_text())['train']
    for pair in pairs:
        x,y=positions[pair['base_id']],positions[pair['matched_id']];d=abs(x//8-y//8);distances.append(d)
        for k in ['all',pair['family']]:
            s=groups[k];s['pair_groups']+=1;s['same_microbatch']+=x//4==y//4;s['same_optimizer_step']+=x//8==y//8
    for model in ['qwen3','qwen35']:
        cfg=json.loads((e/'runs'/(model+'-20261030-targeted-v9-matched')/'stage4/training_config.json').read_text())['args']
        assert cfg['seed']==101 and cfg['epochs']==1 and cfg['batch']==4 and cfg['accum']==2
        if 'length_sort' in cfg:assert cfg['length_sort']==0
    code=(e/'stages/stage3/kev/train.py').read_text()
    assert 'rng.shuffle(reqs)' in code and 'for mb in range(micro_per_epoch):' in code
    assert 'chunk = reqs[mb * a.batch : (mb + 1) * a.batch]' in code
    distances.sort();audit={'rows':len(ids),'matched_groups':len(pairs),'seed':101,'batch':4,'accum':2,'groups':dict(groups),'optimizer_step_distance':{'minimum':min(distances),'median':distances[len(distances)//2],'maximum':max(distances)},'scope':'Exact first-epoch original shuffle indices; preflight verified no filtering. Separate CE on both views is still valid. Rare co-occurrence is not proof of failure cause; grouped batches would test a different stochastic optimization schedule, not create new data.'}
    audit['training_code_sha256']=hashlib.sha256(code.encode()).hexdigest()
    (p/'pair_exposure_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'official_policy':{m:{s:x['strata'] for s,x in v.items()} for m,v in result['models'].items()},'pair_exposure':audit},ensure_ascii=False))


if __name__=='__main__':main()
