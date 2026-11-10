#!/usr/bin/env python3
"""Prepare full 1500-context step-supervision control, original stage3 starts."""
import hashlib
import json
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'targeted_v8_steps_20261030'
SOURCE=BASE/'targeted_v7_lr5_20261030'

def main():
    assert not (OUT/'launch.json').exists()
    (OUT/'train_original.jsonl').write_bytes((BASE/'targeted_v7_20261030/train.jsonl').read_bytes())
    preflight=(SOURCE/'preflight.py').read_text()
    preflight=preflight.replace("Path(output).write_text", "steps=load_records(folder+'/development_steps.jsonl')\nassert len(steps)==334 and all(fits(materialize(r),tok,**training_context(7552)) for r in steps)\nresult['development_step_questions']=sum(len(r['questions']) for r in steps)\nPath(output).write_text")
    (OUT/'preflight.py').write_text(preflight)
    evaluate=(OUT/'evaluate_development.py').read_text().replace('same-generator development; not independent heldout','Diagnostic labeled inputs; identify scope by data path/hash. Training inputs are in-sample and development shares generators.')
    (OUT/'evaluate_development.py').write_text(evaluate)
    gate='''import json,sys,hashlib
from pathlib import Path
run,data,model,original=map(str,sys.argv[1:])
r=Path(run);d=Path(data);root=d.parent
for kind,file in [('development','development.jsonl'),('train-probe','train_probe.jsonl')]:
 report=json.loads((r/(kind+'-before')/'report.json').read_text())
 assert report['data_sha256']==hashlib.sha256((d/file).read_bytes()).hexdigest()
 before=json.loads((r/(kind+'-before')/'rows.json').read_text())
 reference=json.loads((root/'runs'/(model+'-20261030-targeted-v7')/(kind+'-before')/'rows.json').read_text())
 assert before==reference,'Original stage3 baseline changed'
step=json.loads((r/'development-steps-before/report.json').read_text());c=step['coverage']
assert step['data_sha256']==hashlib.sha256((d/'development_steps.jsonl').read_bytes()).hexdigest()
assert c['requested_records']==c['evaluated_records']==334 and c['requested_questions']==c['evaluated_questions']==732 and c['rejected_records']==c['truncated_records']==0
assert step['run']==str(root/'runs'/original/'stage3')
(r/'baseline_gate.json').write_text(json.dumps({'passed':True,'original_development_questions':488,'original_probe_questions':185,'step_development_questions':732},indent=2)+'\\n')
print('Original baselines identical; step development fully covered.',flush=True)
'''
    (OUT/'verify_baseline.py').write_text(gate)
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        s=(SOURCE/('launch_'+model+'.sh')).read_text().replace(SOURCE.name,OUT.name).replace('targeted-v7-lr5','targeted-v8-steps').replace('--lr 5e-5','--lr 1e-5')
        marker="printf 'training\\n' > \"$RUN/status.txt\""
        before=("printf 'development_steps_before\\n' > \"$RUN/status.txt\"\n"+
            f'"$ROOT/python.sh" "$DATA/evaluate_development.py" "$ROOT/runs/{original}/stage3" "$DATA/development_steps.jsonl" "$RUN/development-steps-before"\n'+
            f'"$ROOT/python.sh" "$DATA/verify_baseline.py" "$RUN" "$DATA" {model} {original}\n')
        assert marker in s;s=s.replace(marker,before+marker)
        marker="printf 'full_train_after\\n' > \"$RUN/status.txt\""
        extra="printf 'development_steps_after\\n' > \"$RUN/status.txt\"\n"+'"$ROOT/python.sh" "$DATA/evaluate_development.py" "$RUN/stage4" "$DATA/development_steps.jsonl" "$RUN/development-steps-after"\n'
        assert marker in s;s=s.replace(marker,extra+marker)
        s=s.replace('"$DATA/train.jsonl" "$RUN/full-train-after"','"$DATA/train_original.jsonl" "$RUN/full-train-after"')
        (OUT/('launch_'+model+'.sh')).write_text(s)
    m=json.loads((OUT/'manifest.json').read_text());m.update(status='prepared_remote_preflight_pending')
    m['evaluation_plan']={'before':'Original dev488/probe185 identical to original-stage3 v7 baselines; step dev732 before/after.',
        'after':'Original development and probe, step development, all original 1500 training contexts/2320 primary questions, full hard-v1 and devtools-v1.',
        'success':'Both models must clearly improve all seven real categories; step or training accuracy alone is insufficient.'}
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text('''# Kev 中间步骤监督对照

仍为1500道情境、6000条回放；三个保留类别300道逐行不变。沿用v7四类共1200道情境及所有最终问题，各增加一个可见事实可计算的步骤子问，总子问由2320变为3520。不是新增1200道情境。两模型从原stage3开始，lr1e-5、一轮938步。

概率补条件分母、联合/总标记率、两事件乘积和扣成本前期望；多跳补一轮传播、第一主管、日期可用性、直接多数股权；信息不足补可行数值范围、所需级别和日历边界；政策补明确假设符合条件时的计算、适用限额和第一运算步骤。政策步骤题均保留0候选，但其正确步骤值大于0。原拒赔问题和原标签均保留。

每条弱项只加一个步骤，原主要问题占每条未经增强样本平均CE的至少一半。辅助问题使用one-hot target，只允许选项置换，避免none改写其步骤含义。仍须检查实际增强后的损失份额。模型各问题分支独立，步骤答案不会输入其他问题；这里没有显式答案一致性损失。是否改善真实七类只能由后续评测判断。
''')
    with tarfile.open(OUT/'inputs.tar.gz','w:gz') as t:
        for p in sorted(OUT.iterdir()):
            if p.suffix in ['.py','.sh','.json','.jsonl','.md']:t.add(p,arcname=OUT.name+'/'+p.name,recursive=False)
        for name in ['audit_kev_loss_exposure.py','audit_kev_none_augmentation.py']:t.add(ROOT/'tools'/name,arcname=name,recursive=False)
    print('prepared',hashlib.sha256((OUT/'inputs.tar.gz').read_bytes()).hexdigest())

if __name__=='__main__':main()
