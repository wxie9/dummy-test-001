#!/usr/bin/env python3
"""Freeze the user-authorized one-pass pilot without enlarging the new dataset."""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/kev_training_eval_20261026/targeted_v3_review_20261029'
OUT=ROOT/'artifacts/kev_training_eval_20261026/targeted_v3_pilot_train_20261030'
REMOTE='/C20545/kev-08b-official-repro-20261026'


def main():
    OUT.mkdir(exist_ok=True)
    new=(SOURCE/'new_four_families.review.jsonl').read_bytes().splitlines(keepends=True)
    old=(SOURCE/'retained/train.jsonl').read_bytes().splitlines(keepends=True)
    selected=list(new)
    for family in ('tool_routing','temporal','injection'):
        pool=[line for line in old if json.loads(line)['_meta']['family']==family]
        selected.extend(random.Random('v3pilot:101:'+family).sample(pool,20))
    random.Random(101).shuffle(selected)
    assert len(selected)==128
    assert len({json.loads(x)['_meta']['id'] for x in selected})==128
    path=OUT/'train.jsonl'
    path.write_bytes(b''.join(selected))
    rows=[json.loads(x) for x in selected]
    manifest={
        'date':'2026-10-30','status':'prepared','seed':101,'records':128,
        'questions':sum(len(r['questions']) for r in rows),
        'by_family':dict(Counter(r['_meta']['family'] for r in rows)),
        'train_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'new_contexts':68,'retained_contexts':60,'epochs':1,'batch':4,'accum':2,'planned_optimizer_steps':16,
        'lr':1e-5,'lora_rank':16,'pointer_head':'warm-started and updated at lr=1e-5',
        'replay':0,'synthetic_repeat':1,'option_augmentation':False,
        'source_directory':str(SOURCE),'source_new_sha256':hashlib.sha256(b''.join(new)).hexdigest(),
        'source_ids':[r['_meta']['id'] for r in rows],
        'lineage_note':'All selected JSONL lines are byte-identical to their source. _meta.split describes the source; all 128 rows are now authorized training input for this pilot.',
        'initialization':{'qwen3':'runs/qwen3-06b-20261026/stage3','qwen35':'runs/replica-20261026/stage3'},
        'evaluation':'Frozen hard-v1 test, one option order, date_facts disabled, after training. This is an inspected diagnostic set, not an untouched generalization test.',
        'limits':['One epoch and one seed on 128 contexts is a smoke experiment.','Compared with v2, data volume, replay and augmentation differ; not a data-only causal ablation.',
                  'No general replay beyond the 60 retained-category examples.','No claim of independent generalization from this small pilot.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    preflight='''import json, sys
from pathlib import Path
from kev.data import load_records, materialize
from kev.model import load_tokenizer, fits, training_context
base, revision, data, output = sys.argv[1:]
tok = load_tokenizer(base, revision=revision)
rows = load_records(data)
context = training_context(7552)
rejected = [r['_meta']['id'] for r in rows if not fits(materialize(r), tok, **context)]
summary = {'records':len(rows),'questions':sum(len(r['questions']) for r in rows), 'rejected':rejected, 'context':context, 'max_state_tokens':max(len(tok.encode(r['state'], add_special_tokens=False)) if isinstance(r['state'],str) else len(tok.encode(json.dumps(r['state']),add_special_tokens=False)) for r in rows)}
Path(output).write_text(json.dumps(summary,indent=2)+'\\n')
print(json.dumps(summary), flush=True)
assert len(rows)==128 and not rejected, 'Pilot must train every planned context without silent filtering'
'''
    (OUT/'preflight.py').write_text(preflight)
    for model,gpu,base,rev,init in [
        ('qwen3',1,'/C20545/models/Qwen3-0.6B-Base','local-model-sha256-cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba','qwen3-06b-20261026'),
        ('qwen35',2,'Qwen/Qwen3.5-0.8B-Base','dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68','replica-20261026'),
    ]:
        run=f'{REMOTE}/runs/{model}-20261030-targeted-v3-pilot'
        dataset=f'{REMOTE}/{OUT.name}'
        script=f'''#!/usr/bin/env bash
set -euo pipefail
ROOT={REMOTE}
DATA={dataset}
RUN={run}
test ! -e "$RUN"
mkdir "$RUN"
trap 'code=$?; if [ "$code" -ne 0 ]; then printf "failed exit=%s\\n" "$code" > "$RUN/status.txt"; fi' EXIT
export CUDA_VISIBLE_DEVICES={gpu}
export HF_HOME="$ROOT/hf" HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$ROOT/stages/stage3${{PYTHONPATH:+:$PYTHONPATH}}"
cd "$ROOT/stages/stage3"
printf 'preflight\\n' > "$RUN/status.txt"
"$ROOT/python.sh" "$DATA/preflight.py" '{base}' '{rev}' "$DATA/train.jsonl" "$RUN/preflight.json"
printf 'training\\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.train \\
 --epochs 1 --seed 101 --lr 1e-5 --lora 16 --accum 2 --batch 4 \\
 --perm_kl 0.0 --perm_frac 0.0 --ord_w 0.0 \\
 --p_none 0.0 --p_none_distract 0.0 --p_distract 0.0 --p_none_pair 0.0 \\
 --synthetic_repeat 1 --public_frac 1.0 --head_lr 0.0 --weight_decay 0.01 \\
 --anchor_w 0.0 --label_smoothing 0.0 --brier_w 0.0 --focal_gamma 0.0 \\
 --dtype bf16 --checkpointing 1 --replay 0 --max_state 7552 \\
 --data "$DATA/train.jsonl" --base '{base}' --base_revision '{rev}' \\
 --init_from "$ROOT/runs/{init}/stage3" --suite "$ROOT/evals/v7/decision-v7" \\
 --out "$RUN/stage4" --device cuda
printf 'evaluating_hard_v1\\n' > "$RUN/status.txt"
"$ROOT/python.sh" -m kev.benchmark --run "$RUN/stage4" --suite "$ROOT/evals/hard-v1" \\
 --allow-test --out "$RUN/eval-hard-v1" --device cuda
printf 'complete\\n' > "$RUN/status.txt"
'''
        (OUT/f'launch_{model}.sh').write_text(script)
    (OUT/'README.md').write_text('''# Kev v3 小样本一轮试训（2026-10-30）

用户授权先用审阅题试训。全部68条新情境，加原三类各20条训练记录，128情境/154子题，原始行不改。只跑1 epoch、16次优化更新；LoRA与pointer head均从原stage3加载，学习率1e-5。没有接续v1/v2的stage4。

不额外混入6000条replay，不重复新题，关闭None/干扰选项增强。与v2存在数据量和训练配比差异，因此只作小规模试训，不声称是严格的仅换数据对照。

两模型分别使用GPU1、2。先用各自分词器确认全部128条能装入训练上下文；任何过滤都会终止。然后训练并保存，最后自动评测固定hard-v1。日志在远端数据目录的pipeline-qwen3.log / pipeline-qwen35.log；每个run有status.txt、preflight.json、stage4/和eval-hard-v1/。

hard-v1已参与错误分析，只能作为已知诊断集修复指标。此批review题已用于训练，不能再称独立测试题。启动情况另见run_status.json。
''')
    print(json.dumps({k:v for k,v in manifest.items() if k!='source_ids'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
