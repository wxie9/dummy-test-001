#!/usr/bin/env python3
"""Prepare full-training-corpus before/after inference, never additional training."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
SOURCE=BASE/'targeted_v7_20261030'
OUT=BASE/'v7_training_fit_audit_20261030'

def main():
    assert not (OUT/'launch.json').exists(),'Do not overwrite an already launched audit'
    OUT.mkdir(exist_ok=True)
    source=SOURCE/'train.jsonl';rows=[json.loads(l) for l in source.read_text().splitlines()];assert len(rows)==1500
    (OUT/'train_eval.jsonl').write_bytes(source.read_bytes())
    (OUT/'evaluate.py').write_text((SOURCE/'evaluate_development.py').read_text().replace('same-generator development; not independent heldout','full training-corpus acquisition diagnostic; not generalization'))
    root='/C20545/kev-08b-official-repro-20261026';jobs={}
    for model,original,gpus in [('qwen3','qwen3-06b-20261026',[1,2]),('qwen35','replica-20261026',[3,4])]:
        for stage,gpu in zip(['stage3','v7'],gpus):
            name=model+'-'+stage;checkpoint=root+'/runs/'+(original+'/stage3' if stage=='stage3' else model+'-20261030-targeted-v7/stage4')
            script=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT={root}
DATA="$ROOT/{OUT.name}"
test ! -e "$DATA/{name}"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\\n" "$code" > "$DATA/{name}.status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES={gpu} HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${{PYTHONPATH:+:$PYTHONPATH}}"
printf 'evaluating\\n' > "$DATA/{name}.status.txt"
"$ROOT/python.sh" "$DATA/evaluate.py" "{checkpoint}" "$DATA/train_eval.jsonl" "$DATA/{name}"
printf 'complete\\n' > "$DATA/{name}.status.txt"
'''
            (OUT/('launch_'+name+'.sh')).write_text(script);jobs[name]={'gpu':gpu,'checkpoint':checkpoint}
    manifest={'status':'prepared_not_started','scope':'All 1500 raw training contexts, without training augmentation. Compare original stage3 and completed v7. This is acquisition on training data, not independent generalization.','contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'train_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_experiment':str(SOURCE),'jobs':jobs,'training_performed':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
