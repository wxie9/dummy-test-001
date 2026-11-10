#!/usr/bin/env python3
"""Label-preserving training-input diagnostics; never new training data."""
import copy
import hashlib
import json
import math
import re
import tarfile
from collections import Counter
from functools import reduce
from pathlib import Path
from build_kev_probability_transfer_candidates import read_table, verify as verify_probability
from build_kev_policy_transfer_candidates import verify as verify_policy

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'v7_representation_probe_20261030'
REMOTE='/C20545/kev-08b-official-repro-20261026'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def policy_excerpt(state):
    event=re.search(r'\[Claim facts\]\nEvent: ([^.]+)\.',state)[1]
    pattern=r'\[Cover (C\d+)\] ([^\n]+)\n.*?(?=\n\n|\Z)'
    blocks=list(re.finditer(pattern,state,re.S))
    selected=[b for b in blocks if b[2]==event]
    assert len(selected)==1 and len(blocks)>=2
    # Select solely from the displayed event, not metadata or the target answer.
    result=re.sub(pattern,lambda m:m[0] if m[2]==event else '',state,flags=re.S)
    result=re.sub(r'\n{3,}','\n\n',result)
    return result,{'retained_cover':selected[0][1],'removed_covers':len(blocks)-1}

def table_state(state,small,prose):
    matrix=read_table(state)
    divisor=reduce(math.gcd,[n for row in matrix.values() for n in row.values()]) if small else 1
    def divide(obj):
        if isinstance(obj,int):assert obj%divisor==0;return obj//divisor
        if isinstance(obj,str):return re.sub(r'\b\d+\b',lambda m:str(int(m[0])//divisor) if int(m[0])%divisor==0 else (_ for _ in ()).throw(AssertionError('Non-count number')),obj)
        if isinstance(obj,dict):return {k:divide(v) for k,v in obj.items()}
        if isinstance(obj,list):return [divide(x) for x in obj]
        raise TypeError(type(obj))
    if prose:
        scope=state['audit_scope'] if isinstance(state,dict) else state.splitlines()[0]
        result=scope+'\n'+'\n'.join(name+': '+'; '.join(str(n//divisor)+' '+status for status,n in row.items())+'.' for name,row in matrix.items())
    else:result=divide(state)
    observed=read_table(result)
    assert observed=={name:{status:n//divisor for status,n in row.items()} for name,row in matrix.items()}
    return result,{'count_divisor':divisor,'forced_prose':prose}

def main():
    assert not (OUT/'launch.json').exists(),'An existing probe cannot be rebuilt'
    OUT.mkdir(exist_ok=True)
    src=BASE/'targeted_v7_20261030/train.jsonl'
    raw=[json.loads(l) for l in src.read_text().splitlines()]
    rows=[];mapping=[]
    for r in raw:
        family=r['_meta']['family']
        if family=='policy':variants=[('selected_cover',*policy_excerpt(r['state']))]
        elif family=='probability' and r['_meta']['subtype']=='table':
            variants=[(name,*table_state(r['state'],small,prose)) for name,small,prose in [('small_counts',True,False),('prose',False,True),('small_counts_prose',True,True)]]
        else:continue
        for name,state,details in variants:
            x=copy.deepcopy(r);rid=r['_meta']['id'];x['_meta']['id']=rid+'/diagnostic/'+name;x['_meta']['group_id']=rid
            x['_meta']['diagnostic']={'original_id':rid,'variant':name,**details};x['state']=state
            assert x['questions']==r['questions']
            if family=='policy':verify_policy(x)
            else:verify_probability(x)
            x['_meta']['text_sha256']=hashlib.sha256(json.dumps(state,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            mapping.append({'id':x['_meta']['id'],'original_id':rid,'family':family,'variant':name,'subtype':r['_meta']['subtype'],
                'state_unchanged':state==r['state'],'before_chars':len(json.dumps(r['state'],ensure_ascii=False)),
                'after_chars':len(json.dumps(state,ensure_ascii=False)),**details})
            rows.append(x)
    assert Counter(x['variant'] for x in mapping)=={'selected_cover':300,'small_counts':75,'prose':75,'small_counts_prose':75}
    path=OUT/'probe.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
    assert sum(len(r['questions']) for r in rows)==1050
    # Recheck serialized inputs rather than only in-memory construction.
    for r in map(json.loads,path.read_text().splitlines()):
        (verify_policy if r['_meta']['family']=='policy' else verify_probability)(r)
    (OUT/'mapping.json').write_text(json.dumps(mapping,indent=2)+'\n')
    evaluator=(BASE/'targeted_v7_20261030/evaluate_development.py').read_text().replace('same-generator development; not independent heldout','label-preserving representation ablations of training inputs; not generalization or new training')
    (OUT/'evaluate.py').write_text(evaluator)
    jobs={}
    for model,original,gpus in [('qwen3','qwen3-06b-20261026',[1,2]),('qwen35','replica-20261026',[3,4])]:
        for stage,gpu in zip(['stage3','lr5'],gpus):
            name=model+'-'+stage
            checkpoint=REMOTE+'/runs/'+(original+'/stage3' if stage=='stage3' else model+'-20261030-targeted-v7-lr5/stage4')
            baseline=REMOTE+('/v7_training_fit_audit_20261030/'+model+'-stage3' if stage=='stage3' else '/runs/'+model+'-20261030-targeted-v7-lr5/full-train-after')
            jobs[name]={'gpu':gpu,'checkpoint':checkpoint,'baseline':baseline}
            script=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT={REMOTE}
DATA="$ROOT/{OUT.name}"
test ! -e "$DATA/{name}"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\\n" "$code" > "$DATA/{name}.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES={gpu} HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${{PYTHONPATH:+:$PYTHONPATH}}"
printf 'evaluating\\n' > "$DATA/{name}.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "{checkpoint}" "$DATA/probe.jsonl" "$DATA/{name}"
printf 'complete\\n' > "$DATA/{name}.status.txt"
'''
            (OUT/('launch_'+name+'.sh')).write_text(script)
    manifest={'status':'prepared_not_started','training_performed':False,'source_sha256':sha(src),'probe_sha256':sha(path),
        'contexts':525,'questions':1050,'original_contexts_reused':375,'jobs':jobs,
        'checks':{'all_question_objects_unchanged':True,'all_labels_recomputed_from_visible_text':True},
        'scope':'Inference-only ablations on existing training cases, not a new 1500-context training dataset. Cached original-input predictions provide matched baselines. No test records or labels used.',
        'limits':['The policy selector removes irrelevant covers using an exact visible-event match; it supplies retrieval help and changes length together.',
                  'Table scaling preserves probabilities, not literal population counts; valid only for the unchanged conditional-percentage questions.',
                  'These cases were trained on and this is not independent generalization.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with tarfile.open(OUT/'inputs.tar.gz','w:gz') as t:
        for p in sorted(OUT.iterdir()):
            if p.suffix in ['.json','.jsonl','.py','.sh']:t.add(p,arcname=OUT.name+'/'+p.name,recursive=False)
    print(json.dumps({'contexts':525,'questions':1050,'originals':375,'unchanged_controls':sum(m['state_unchanged'] for m in mapping),'sha256':sha(path)}))

if __name__=='__main__':main()
