#!/usr/bin/env python3
"""Prepare one-epoch wording control without changing any source data."""
from pathlib import Path
import json
import hashlib

root=Path(__file__).resolve().parents[1]/'artifacts/kev_training_eval_20261026'
source=root/'targeted_v6_20261030';out=root/'targeted_v6_factmix_candidate_20261030'
manifest=json.loads((out/'manifest.json').read_text())
assert manifest['status']=='validated_candidate_not_trained'
assert manifest['checks']['both_model_preflight_all_7500_accepted']
assert manifest['checks']['server_three_epoch_augmentation_identical']
assert hashlib.sha256((out/'train.jsonl').read_bytes()).hexdigest()=='2f50313e50370372cf232a998280a4f5bbc26f98dd59ddef2ee8872f870fe243'
for model,old_gpu,gpu,original in [('qwen3',1,3,'qwen3-06b-20261026'),('qwen35',2,4,'replica-20261026')]:
    text=(source/f'launch_{model}.sh').read_text()
    text=text.replace('targeted_v6_20261030',out.name).replace('targeted-v6','targeted-v6-factmix')
    text=text.replace(f'CUDA_VISIBLE_DEVICES={old_gpu}',f'CUDA_VISIBLE_DEVICES={gpu}')
    assert text.count('--epochs 1')==1
    assert '--init_from "$ROOT/runs/'+original+'/stage3"' in text
    assert 'test ! -e "$RUN"' in text
    (out/f'launch_{model}.sh').write_text(text)
manifest['status']='prepared_not_launched'
manifest['training_plan']={'epochs':1,'expected_optimizer_steps':938,'seed':101,'lr':1e-5,'lora':16,'batch':4,'accum':2,'replay':6000,
  'init':'original pre-targeted stage3; never targeted stage4','gpus':{'qwen3':3,'qwen35':4},
  'purpose':'Single-factor fact-wording replacement versus completed v6 one epoch; evaluate all seven categories. Concurrent v6 three-epoch run isolates exposure separately.'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['training_plan'],ensure_ascii=False))
