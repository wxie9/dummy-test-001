#!/usr/bin/env python3
"""Prepare an isolated one-epoch guard ablation; launch is a separate action."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args()
    source=a.root/'targeted_v5_3ep_20261030'
    out=a.root/'targeted_v5_none_guard_candidate_20261030'
    assert out.is_dir()
    assert hashlib.sha256((out/'train.jsonl').read_bytes()).hexdigest()=='7d2493876883c394f36e6c26389a102d9dab99b187915f0f6eaf283106ac7e52'
    for name in ['development.jsonl','train_probe.jsonl','train_probe_manifest.json','preflight.py','evaluate_development.py','evaluate_train_probe.py']:
        (out/name).write_bytes((source/name).read_bytes())
    for model,oldgpu,newgpu in [('qwen3',1,3),('qwen35',2,4)]:
        s=(source/f'launch_{model}.sh').read_text()
        s=s.replace('targeted_v5_3ep_20261030','targeted_v5_none_guard_candidate_20261030')
        s=s.replace('targeted-v5-3ep','targeted-v5-guard')
        s=s.replace('--epochs 3','--epochs 1')
        s=s.replace(f'CUDA_VISIBLE_DEVICES={oldgpu}',f'CUDA_VISIBLE_DEVICES={newgpu}')
        assert '--epochs 1' in s and '--epochs 3' not in s
        assert s.count(f'CUDA_VISIBLE_DEVICES={newgpu}')==2
        (out/f'launch_{model}.sh').write_text(s)
    manifest=json.loads((out/'train.manifest.json').read_text())
    manifest.update(status='prepared_not_launched',epochs=1,seed=101,lr=1e-5,lora=16,replay=6000,
        init='original pre-targeted stage3',planned_updates=938,
        run_version='v5-guard',reference='v5 one epoch',
        intention='Single data-augmentation guard ablation; preserve all 1500 original states, labels and options. Not a test of other candidate components.',
        success_status='unproven',goal_achieved=False)
    (out/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Prepared two 1-epoch pipelines on GPUs3/4; not launched.')

if __name__=='__main__':main()
