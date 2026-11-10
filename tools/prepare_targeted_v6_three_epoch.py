#!/usr/bin/env python3
"""Freeze v6 data for an exposure control; original stage3 initialization."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/kev_training_eval_20261026/targeted_v6_20261030'
OUT=SOURCE.with_name('targeted_v6_3ep_20261030')

def main():
    OUT.mkdir(exist_ok=True)
    for name in ['train.jsonl','development.jsonl','train_probe.jsonl','preflight.py','evaluate_development.py',
                 'none_guard_records.json','none_augmentation_with_replay.json']:
        src=SOURCE/name;dst=OUT/name
        if dst.exists():assert dst.read_bytes()==src.read_bytes(),name
        else:dst.write_bytes(src.read_bytes())
    for model in ['qwen3','qwen35']:
        original=(SOURCE/f'launch_{model}.sh').read_text()
        text=original.replace('targeted_v6_20261030',OUT.name).replace('targeted-v6','targeted-v6-3ep')
        assert text.count('--epochs 1')==1
        text=text.replace('--epochs 1','--epochs 3')
        assert '--init_from "$ROOT/runs/'+('qwen3-06b-20261026' if model=='qwen3' else 'replica-20261026')+'/stage3"' in text
        (OUT/f'launch_{model}.sh').write_text(text)
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    manifest.update(experiment='targeted-v6-3ep-20261030',status='prepared_not_launched',data_version_unchanged=manifest['version'])
    manifest['training_plan'].update(epochs=3,expected_optimizer_steps=2814,
        init='original pre-targeted stage3; never a targeted stage4 checkpoint',
        purpose='Only epochs changes from v6 one epoch to three; OneCycleLR spans the longer run. Diagnose acquisition vs transfer, not guaranteed gain.')
    hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['train.jsonl','development.jsonl','train_probe.jsonl']}
    for name,value in hashes.items():assert value==hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
    manifest['unchanged_data_hashes']=hashes
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text('''# Kev v6 固定数据三轮对照

保持v6的1500个情境、3440个子问、6000条回放、开发集和训练探针完全一致；两模型均从原stage3初始化。仅把训练轮数从1改为3，其余参数相同，OneCycle学习率计划相应延长至2814次更新。

动机：v6一轮后，多跳训练探针Qwen3为8→8/30、Qwen3.5为10→15/30，真实多跳均下降；概率训练探针也只小幅提高。这组对照检查训练样本是否能够进一步学会，并同时检查全部七类旧错题和新增错误。不预设增加训练量能解决问题。

不是从v6一轮权重接着训练。唯一情境数量仍为1500，三次遍历不记成4500个新情境。原三类已知歧义保持原样，现有诊断评测不是全新盲测。结果未完成前不作提升结论。
''')
    print(json.dumps({'directory':str(OUT),'hashes':hashes,'epochs':3,'expected_steps':2814},indent=2))

if __name__=='__main__':main()
