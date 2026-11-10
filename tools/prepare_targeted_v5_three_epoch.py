#!/usr/bin/env python3
"""Fixed-data exposure experiment motivated by v5's low train-probe accuracy."""
import hashlib
import json
from pathlib import Path
from build_targeted_v5 import OUT as SOURCE

OUT=SOURCE.with_name('targeted_v5_3ep_20261030')

def main():
    OUT.mkdir(exist_ok=True)
    for name in ['train.jsonl','development.jsonl','train_probe.jsonl','train_probe_manifest.json','preflight.py','evaluate_development.py','evaluate_train_probe.py']:
        src=SOURCE/name;dst=OUT/name
        if dst.exists():assert dst.read_bytes()==src.read_bytes(),name
        else:dst.write_bytes(src.read_bytes())
    for model in ['qwen3','qwen35']:
        s=(SOURCE/f'launch_{model}.sh').read_text().replace('targeted_v5_20261030',OUT.name).replace('targeted-v5','targeted-v5-3ep')
        assert s.count('--epochs 1')==1;s=s.replace('--epochs 1','--epochs 3')
        original='qwen3-06b-20261026' if model=='qwen3' else 'replica-20261026'
        before=f'"$ROOT/python.sh" "$DATA/evaluate_train_probe.py" "$ROOT/runs/{original}/stage3" "$DATA/train_probe.jsonl" "$RUN/train-probe-before"\n'
        after='"$ROOT/python.sh" "$DATA/evaluate_train_probe.py" "$RUN/stage4" "$DATA/train_probe.jsonl" "$RUN/train-probe-after"\n'
        s=s.replace("printf 'training\\n'",before+"printf 'training\\n'")
        s=s.replace("printf 'complete\\n'", "printf 'train_probe_after\\n' > \"$RUN/status.txt\"\n"+after+"printf 'complete\\n'")
        (OUT/f'launch_{model}.sh').write_text(s)
    m=json.loads((SOURCE/'manifest.json').read_text())
    m['experiment']='targeted-v5-3ep-20261030';m['status']='prepared_not_launched'
    m['data_version_unchanged']=m['version'];m['training_plan']['epochs']=3
    m['training_plan']['purpose']='Fixed-data exposure comparison: only epochs changes from 1 to 3; OneCycleLR spans the longer run.'
    m['training_plan']['expected_optimizer_steps']=2814
    m['training_plan']['init']='original pre-targeted stage3; never v5 stage4'
    m['limitations']=['Known retained temporal wording and tool-routing semantic issues remain unchanged pending clarification.','This experiment diagnoses learning strength, not data-quality repair.','Single seed and previously inspected diagnostic benchmarks.']
    for name in ['train.jsonl','development.jsonl','train_probe.jsonl']:
        assert hashlib.sha256((OUT/name).read_bytes()).digest()==hashlib.sha256((SOURCE/name).read_bytes()).digest()
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print(str(OUT))

if __name__=='__main__':main()
