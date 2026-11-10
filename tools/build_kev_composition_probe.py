#!/usr/bin/env python3
"""Frozen-checkpoint diagnostics for queried graph depth and payment eligibility.

Not a training corpus. Graph variants share 30 source graph groups; policy
variants reuse 120 positive training claims. Official examples are not copied.
"""
import copy
import hashlib
import json
import random
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from build_kev_policy_transfer_candidates import verify as verify_policy

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'v8_composition_probe_20261030'
REMOTE='/C20545/kev-08b-official-repro-20261026'
NAMES=['amber','birch','cobalt','dune','elm','flint','garnet','hemlock','iris','juniper','kelp','larch','mica','nutmeg','onyx','pine','reed','slate','thyme','umber']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def money(s):return float(s.replace('$','').replace(',',''))

def distances(edges,down):
    d={down:0}
    for _ in range(len(edges)+1):
        changed=False
        for consumer,prerequisite,hard in edges:
            if hard and prerequisite in d and (consumer not in d or d[consumer]>d[prerequisite]+1):
                d[consumer]=d[prerequisite]+1;changed=True
        if not changed:return d
    raise AssertionError('Nonconvergent distance calculation')

def verify_graph(row):
    text=row['state'];edges=[(a,b,t=='hard') for a,b,t in re.findall(r'([\w-]+) depends on ([\w-]+) \((hard|soft)\)\.',text)]
    assert len(edges)==8
    down=re.search(r'Initial outage: ([\w-]+)\.',text)[1]
    affected=set(distances(edges,down));q=row['questions']['affected']
    matching=[k for k,value in q['criteria'].items() if value in affected]
    assert len(matching)<=1
    label=matching[0] if matching else next(k for k,v in q['criteria'].items() if v=='None of these services fails')
    assert q['label']==label
    return distances(edges,down)

def graph_group(i):
    rng=random.Random('kev-composition-graph-v1/'+str(i))
    names=[x+'-'+rng.choice(['worker','router','store','processor']) for x in rng.sample(NAMES,10)]
    down,target,*rest=names;bridges=rest[:3];upstream,unrelated,root,soft,softchild=rest[3:]
    values=[target,upstream,unrelated,softchild,'None of these services fails'];rng.shuffle(values)
    order=list(range(8));rng.shuffle(order)
    for depth in [1,2,3,4]:
        for blocked in [False,True]:
            chain=[down]+bridges[:depth-1]+[target]
            edges=[(b,a,not(blocked and b==target)) for a,b in zip(chain,chain[1:])]
            edges += [(b,root,True) for b in bridges[depth-1:]]
            edges += [(down,upstream,True),(unrelated,root,True),(soft,down,False),(softchild,soft,True)]
            assert len(edges)==8
            state='SERVICE INCIDENT\nA service fails if a hard prerequisite fails. Repeat until no more services fail. A soft prerequisite failure does not disable its consumer. Failure does not travel from consumer to prerequisite. All dependencies are listed.\n'
            state+='\n'.join(f'{edges[j][0]} depends on {edges[j][1]} ({"hard" if edges[j][2] else "soft"}).' for j in order)
            state+=f'\nInitial outage: {down}. Every other service initially works.'
            expected='None of these services fails' if blocked else target
            criteria=dict(zip('abcde',values));label=next(k for k,v in criteria.items() if v==expected)
            rid=f'composition-graph-v1/{i}/depth-{depth}/blocked-{blocked}'
            row={'state':state,'questions':{'affected':{'type':'choice','instructions':'After all failures have propagated, which listed service fails?','criteria':criteria,'label':label,'src':'composition_graph'}},
                 '_meta':{'id':rid,'group_id':f'composition-graph-v1/{i}','source':'composition_graph','family':'graph_probe','subtype':'dependency','depth':depth,'blocked':blocked,'queried_target':target,'split':'diagnostic'}}
            d=verify_graph(row)
            assert (target not in d) if blocked else d[target]==depth
            yield row

def coverage_audit(train,test,pairs):
    result={'scope':'Post-hoc coverage diagnosis, not evidence that graph depth causes errors. Training hard=True and official soft=True flags are normalized before computing actual queried distance.','splits':{},'model_groups':{}}
    depths={}
    for split,rows in [('train',train),('official_diagnostic',test)]:
        counts=Counter();details=[]
        for row in rows:
            m=row['_meta']
            if split=='train' and not(m.get('family')=='multihop' and m.get('subtype')=='dependency_candidates'):continue
            if split!='train' and m.get('subtype')!='deps':continue
            f=m['facts'];edges=[(a,b,t if split=='train' else not t) for a,b,t in f['edges']]
            d=distances(edges,f.get('initial',f.get('down')));q=next(iter(row['questions'].values()))
            value=q['criteria'][q['label']] if split=='train' else q['label'].replace('_','-')
            depth=str(d[value]) if value in d else 'none';counts[depth]+=1
            details.append({'id':m['id'],'queried_distance':depth,'nominal_chain_hops':m.get('hops',f.get('chain_hops'))})
            if split!='train':depths[m['id']]=depth
        result['splits'][split]={'counts':dict(counts),'contexts':details}
    for model in ['qwen3','qwen35']:
        groups=defaultdict(lambda:Counter())
        for p in pairs:
            if p['model']!=model or p['id'] not in depths:continue
            c=groups[depths[p['id']]];c['questions']+=1;c['before_correct']+=p['before_ok'];c['after_correct']+=p['after_ok']
            c['repaired']+=not p['before_ok'] and p['after_ok'];c['newly_wrong']+=p['before_ok'] and not p['after_ok']
        result['model_groups'][model]={k:dict(v) for k,v in groups.items()}
    return result

def main():
    assert not (OUT/'launch.json').exists(),'Do not rebuild a launched diagnostic'
    OUT.mkdir(exist_ok=True)
    parent=BASE/'targeted_v8_steps_20261030';src=parent/'train_original.jsonl'
    train=[json.loads(l) for l in src.read_text().splitlines()]
    rows=list(r for i in range(30) for r in graph_group(i));mapping=[]
    for r in rows:mapping.append({'id':r['_meta']['id'],'family':'graph_probe','group':r['_meta']['group_id'],'depth':r['_meta']['depth'],'blocked':r['_meta']['blocked']})
    for original in train:
        if original['_meta']['family']!='policy':continue
        q=original['questions']['amount']
        if money(q['criteria'][q['label']])<=0:continue
        verify_policy(original)
        assert original['questions']['reason']['criteria'][original['questions']['reason']['label']].startswith('Pay ')
        for variant in ['original','eligibility_given']:
            r=copy.deepcopy(original);rid=original['_meta']['id'];r['_meta'].update(id=rid+'/composition/'+variant,group_id=rid,source='composition_policy',family='policy_probe',original_id=rid,variant=variant,split='diagnostic')
            if variant=='eligibility_given':
                r['questions']['amount']['instructions']='Assume that this claim satisfies purchase status, waiting and notice periods, and all eligibility and exclusion conditions. Using the assessed loss, applicable ceilings and the stated deductible order, what dollar amount is payable?'
            assert r['state']==original['state']
            for qid,spec in r['questions'].items():
                for key in set(spec)-{'instructions'}:assert spec[key]==original['questions'][qid][key]
            verify_policy(r);rows.append(r)
            mapping.append({'id':r['_meta']['id'],'family':'policy_probe','group':rid,'variant':variant,'original_id':rid,'zero_offered':any(money(v)==0 for v in q['criteria'].values()),'gold_amount':money(q['criteria'][q['label']])})
    assert len(rows)==480 and sum(len(r['questions']) for r in rows)==720
    assert len({r['_meta']['id'] for r in rows})==480
    rejected=0
    for row in rows:
        checker=verify_graph if row['_meta']['family']=='graph_probe' else verify_policy
        for qid,q in row['questions'].items():
            for wrong in q['criteria']:
                if wrong==q['label']:continue
                bad=copy.deepcopy(row);bad['questions'][qid]['label']=wrong
                try:checker(bad)
                except AssertionError:rejected+=1
                else:raise AssertionError(('Accepted wrong label',row['_meta']['id'],qid))
    data=OUT/'probe.jsonl';data.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    for r in map(json.loads,data.read_text().splitlines()):(verify_graph if r['_meta']['family']=='graph_probe' else verify_policy)(r)
    (OUT/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    test_path=parent/'evidence/evals/hard-v1/test.jsonl';pairs_path=parent/'paired-seven.jsonl'
    test=[json.loads(l) for l in test_path.read_text().splitlines()];pairs=[json.loads(l) for l in pairs_path.read_text().splitlines()]
    audit=coverage_audit(train,test,pairs);audit['source_hashes']={str(x):sha(x) for x in [src,test_path,pairs_path]}
    (OUT/'queried_depth_coverage.json').write_text(json.dumps(audit,indent=2)+'\n')
    evaluator=(parent/'evaluate_development.py').read_text().replace('same-generator development; not independent heldout','composition diagnostics with controlled graph variants and eligibility assumptions; not benchmark performance')
    (OUT/'evaluate.py').write_text(evaluator)
    jobs={}
    for model,original,gpus in [('qwen3','qwen3-06b-20261026',[1,2]),('qwen35','replica-20261026',[3,4])]:
        for stage,gpu in zip(['stage3','v8'],gpus):
            name=model+'-'+stage;cp=REMOTE+'/runs/'+(original+'/stage3' if stage=='stage3' else model+'-20261030-targeted-v8-steps/stage4')
            baseline=REMOTE+('/v7_training_fit_audit_20261030/'+model+'-stage3' if stage=='stage3' else '/runs/'+model+'-20261030-targeted-v8-steps/full-train-after')
            jobs[name]={'gpu':gpu,'checkpoint':cp,'baseline':baseline}
            script=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT={REMOTE}
DATA="$ROOT/{OUT.name}"
test ! -e "$DATA/{name}"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\\n" "$code" > "$DATA/{name}.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES={gpu} HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${{PYTHONPATH:+:$PYTHONPATH}}"
printf 'evaluating\\n' > "$DATA/{name}.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "{cp}" "$DATA/probe.jsonl" "$DATA/{name}"
printf 'complete\\n' > "$DATA/{name}.status.txt"
'''
            (OUT/('launch_'+name+'.sh')).write_text(script)
    manifest={'status':'prepared_not_started','training_performed':False,'contexts':480,'questions':720,'independent_new_graph_groups':30,'graph_views':240,'reused_positive_policy_contexts':120,'policy_views':240,
              'source_sha256':sha(src),'probe_sha256':sha(data),'wrong_label_mutations_rejected':rejected,'jobs':jobs,
              'scope':'Inference-only diagnosis. Policy eligibility is privileged truthful information on known eligible training claims; any improvement is not deployable or official benchmark improvement. Thirty graphs have eight related variants each; variants are not independent training contexts.',
              'limits':['Question wording and supplied eligibility change together; cannot attribute effect to a single wording feature.','Graph topology varies along with path depth, while candidate answers, ordering, edge count and node names are held fixed within each group.','Same-author visible-label checks are not independent external review.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with tarfile.open(OUT/'inputs.tar.gz','w:gz') as t:
        for p in sorted(OUT.iterdir()):
            if p.suffix in ['.json','.jsonl','.py','.sh']:t.add(p,arcname=OUT.name+'/'+p.name,recursive=False)
    print(json.dumps({'contexts':480,'questions':720,'rejected':rejected,'probe_sha256':sha(data),'archive_sha256':sha(OUT/'inputs.tar.gz'),'queried_depth_counts':{k:v['counts'] for k,v in audit['splits'].items()}}))

if __name__=='__main__':main()
