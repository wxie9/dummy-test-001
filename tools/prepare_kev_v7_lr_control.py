#!/usr/bin/env python3
"""One-factor v7 learning-rate control; fixed data and original stage3 starts."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
SOURCE=BASE/'targeted_v7_20261030'
OUT=BASE/'targeted_v7_lr5_20261030'

def main():
    assert not (OUT/'launch.json').exists(),'Do not overwrite a launched control'
    OUT.mkdir(exist_ok=True)
    for name in ['train.jsonl','development.jsonl','train_probe.jsonl','preflight.py','evaluate_development.py','augmentation_audit.json']:(OUT/name).write_bytes((SOURCE/name).read_bytes())
    for model in ['qwen3','qwen35']:
        original=(SOURCE/('launch_'+model+'.sh')).read_text()
        text=original.replace('targeted_v7_20261030',OUT.name).replace('targeted-v7','targeted-v7-lr5')
        assert text.count('--lr 1e-5')==1;text=text.replace('--lr 1e-5','--lr 5e-5')
        marker="printf 'hard_v1\\n' > \"$RUN/status.txt\""
        assert marker in text
        text=text.replace(marker,"printf 'full_train_after\\n' > \"$RUN/status.txt\"\n"+'"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/train.jsonl" "$RUN/full-train-after"\n'+marker)
        assert '--epochs 1' in text and '--head_lr 0.0' in text
        (OUT/('launch_'+model+'.sh')).write_text(text)
    m=json.loads((SOURCE/'manifest.json').read_text())
    for k in ['results_summary','train_probe_rendering_audit']:m.pop(k,None)
    m.update(experiment='targeted-v7-lr5-20261030',status='prepared_not_launched',goal_achieved=False,data_version_unchanged='targeted-v7-20261030')
    m['training_plan'].update(lr=5e-5,epochs=1,expected_optimizer_steps=938,purpose='Change only the common learning rate from 1e-5 to 5e-5. head_lr=0 inherits lr, so both LoRA and head receive the same rate increase. Data, order, augmentation, replay, seed, schedule length and original stage3 starts remain unchanged.')
    m['unchanged_data_hashes']={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['train.jsonl','development.jsonl','train_probe.jsonl']}
    assert all(value==hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name,value in m['unchanged_data_hashes'].items())
    m['evaluation_plan']={'before':'Development and training probe must reproduce v7 original-stage3 probabilities exactly. Full training baseline is the verified v7_training_fit_audit stage3 prediction.','after':'Development, 140-context probe, all 1500 raw training contexts, and complete hard-v1/devtools-v1.','success':'All-seven real-benchmark improvement for both models remains required. Training acquisition alone is not success.'}
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text('''# Kev v7 学习率对照

固定v7全部1500条定向情境、6000条回放、开发集、探针、seed和一轮938步；两模型都从原stage3开始。只将共同学习率从1e-5改为5e-5。head_lr=0在代码中继承lr，因此LoRA和head一起使用新学习率。

动机来自全训练集推理：v7一轮后Q3/Q3.5概率仅261/720、319/720；政策正金额仅9/120、26/120。许多训练内规则尚未掌握。较小更新强度是待检验假设，不是已证明原因；学习率提高也可能增加遗忘或退化。

本轮在常规开发/探针/真实评测之外增加全部1500训练情境的after推理，复用已核验的原stage3全量预测。训练分数提升不能代替真实七类提升。不是接续v7 checkpoint，不改数据，不将重复遍历计为新情境。结果未完成前不宣称有效。
''')
    print(json.dumps({'directory':str(OUT),'lr':5e-5,'epochs':1,'data_hashes':m['unchanged_data_hashes']},indent=2))

if __name__=='__main__':main()
