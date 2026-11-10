#!/usr/bin/env python3
"""Four framing conditions for the same 30 synthetic development contexts.

All five questions, options and labels are held fixed. No training launches.
"""
import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from check_targeted_v4_rules import materialize, missing
from build_kev_insufficient_multiview_candidates import verify

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/kev_training_eval_20261026/targeted_v6_20261030'
OUT=SOURCE.with_name('fact_surface_probe_20261030')
WARNING='An unlisted field is not available; do not assume a default value.'
VERSION='fact-surface-probe-20261030'

def tree(value,fn):
    if isinstance(value,str):return fn(value)
    if isinstance(value,dict):return {k:tree(v,fn) for k,v in value.items()}
    if isinstance(value,list):return [tree(v,fn) for v in value]
    raise TypeError(type(value))

def prose(s):
    for old,new in [('Order date','The order was placed on'),('Return requested','A return was requested on'),('Delivered','Delivery occurred on')]:
        s=re.sub(re.escape(old)+r': (\d{4}-\d{2}-\d{2})\.',lambda m:new+' '+datetime.strptime(m[1],'%Y-%m-%d').strftime('%B %d, %Y')+'.',s)
    s=re.sub(r'Merchandise subtotal: \$(\d+)\.',lambda m:f'The merchandise has a pre-discount total of ${int(m[1]):.2f}.',s)
    s=re.sub(r'Merchandise discount: \$(\d+)\.',lambda m:f'The applied discount reduces that amount by ${int(m[1]):.2f}.',s)
    def hours(m):
        a,b,c,d=json.loads(m[1])
        return f'The recorded hours are Monday {a}, Tuesday {b}, Wednesday {c}, and Thursday {d}.'
    s=re.sub(r'Monday through Thursday hours: (\[[^\]]+\])\.',hours,s)
    s=re.sub(r'Friday hours: (\d+)\.',lambda m:f'The Friday shift lasted {m[1]} hours.',s)
    return s

def unprose(s):
    for old,new in [('Order date','The order was placed on'),('Return requested','A return was requested on'),('Delivered','Delivery occurred on')]:
        s=re.sub(re.escape(new)+r' ([A-Za-z]+ \d{2}, \d{4})\.',lambda m:old+': '+datetime.strptime(m[1],'%B %d, %Y').strftime('%Y-%m-%d')+'.',s)
    s=re.sub(r'The merchandise has a pre-discount total of \$(\d+)\.00\.',lambda m:f'Merchandise subtotal: ${int(m[1])}.',s)
    s=re.sub(r'The applied discount reduces that amount by \$(\d+)\.00\.',lambda m:f'Merchandise discount: ${int(m[1])}.',s)
    s=re.sub(r'The recorded hours are Monday (\d+), Tuesday (\d+), Wednesday (\d+), and Thursday (\d+)\.',lambda m:'Monday through Thursday hours: '+json.dumps([int(m[i]) for i in range(1,5)])+'.',s)
    s=re.sub(r'The Friday shift lasted (\d+) hours\.',lambda m:f'Friday hours: {m[1]}.',s)
    return s

def main():
    OUT.mkdir(exist_ok=True)
    source=[json.loads(l) for l in (SOURCE/'development.jsonl').read_text().splitlines()]
    selected=[r for r in source if r['_meta']['family']=='insufficient' and r['_meta']['subtype'].split('__')[0] in ['return','shipping','overtime']]
    assert len(selected)==30
    rows=[]
    for original in selected:
        verify(original)
        clean=tree(original['state'],lambda s:s.replace(WARNING,''))
        for mode in ['original','without_warning','prose','prose_without_warning']:
            r=copy.deepcopy(original)
            is_prose=mode.startswith('prose');without='without_warning' in mode
            if without:r['state']=copy.deepcopy(clean)
            if is_prose:r['state']=tree(r['state'],prose)
            reconstructed=tree(r['state'],unprose) if is_prose else r['state']
            assert reconstructed==(clean if without else original['state'])
            if is_prose:assert r['state']!=reconstructed
            canonical=copy.deepcopy(r);canonical['state']=reconstructed
            verify(canonical)
            assert r['questions']==original['questions']
            r['_meta'].update(id=VERSION+'/'+mode+'/'+original['_meta']['id'],
                group_id=original['_meta']['group_id'],probe_parent_id=original['_meta']['id'],
                probe_condition=mode,original_has_warning=WARNING in json.dumps(original['state']),
                source=VERSION)
            materialize(r);rows.append(r)
    p=OUT/'probe.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    manifest={'status':'prepared_inference_only','parent_contexts':30,'probe_presentations':len(rows),'questions':sum(len(r['questions']) for r in rows),
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'conditions':['original','without_warning','prose','prose_without_warning'],
        'warning_present_parent_contexts':sum(WARNING in json.dumps(r['state']) for r in selected),
        'scope':'Synthetic development cases already used for diagnosis. Uniform framing interventions, unchanged rules, facts, questions, labels and options. No per-item best wording selection. Removing the warning changes no factual information. Prose is invertible to the original fact strings; this does not prove broad semantic robustness.',
        'required_control':'Original condition predictions must match the full five-question native v6 development evaluations exactly before interpretation.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'evaluate.py').write_bytes((SOURCE/'evaluate_development.py').read_bytes())
    for model,gpu,original in [('qwen3',3,'qwen3-06b-20261026'),('qwen35',4,'replica-20261026')]:
        s=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT=/C20545/kev-08b-official-repro-20261026
DATA="$ROOT/fact_surface_probe_20261030"
export CUDA_VISIBLE_DEVICES={gpu} HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3"
test ! -e "$DATA/{model}_stage3"
test ! -e "$DATA/{model}_v6"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/{original}/stage3" "$DATA/probe.jsonl" "$DATA/{model}_stage3"
"$ROOT/python.sh" "$DATA/evaluate.py" "$ROOT/runs/{model}-20261030-targeted-v6/stage4" "$DATA/probe.jsonl" "$DATA/{model}_v6"
printf 'complete\\n' > "$DATA/{model}.status"
'''
        (OUT/('launch_'+model+'.sh')).write_text(s)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
