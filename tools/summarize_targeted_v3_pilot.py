#!/usr/bin/env python3
"""Compare the completed pilot with the cached pre-targeted stage3 predictions."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'targeted_v3_pilot_train_20261030'
AUDIT=BASE/'audit_three_families_20261029'


def correct(r):return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']


def main():
    src=OUT/'evidence/targeted_v3_pilot_train_20261030/eval_source_sha256.txt'
    expected=src.read_text().split()[0]
    test=ROOT/'third_party/kev-source-20261025/evals/hard-v1/test.jsonl'
    assert hashlib.sha256(test.read_bytes()).hexdigest()==expected
    tags={(r['id'],r['question']):r for r in map(json.loads,(AUDIT/'all_questions.jsonl').read_text().splitlines())}
    results={};paired=[];inputs={}
    for model,baseline in [('qwen3','q3_before'),('qwen35','q35_before')]:
        run=OUT/'evidence/runs'/f'{model}-20261030-targeted-v3-pilot'
        assert (run/'status.txt').read_text().strip()=='complete'
        bp=AUDIT/'raw'/f'{baseline}.json';ap=run/'eval-hard-v1/rows.json'
        inputs[model]={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (bp,ap)}
        before={(r['id'],r['question']):r for r in json.loads(bp.read_text())}
        after={(r['id'],r['question']):r for r in json.loads(ap.read_text())}
        assert len(before)==len(after)==1088 and before.keys()==after.keys()
        groups=defaultdict(list)
        for key,b in before.items():
            a=after[key]
            assert a['keys']==b['keys'] and a['label']==b['label']
            item={'model':model,'id':key[0],'question':key[1],'source':a['source'],
                  'before_ok':correct(b),'after_ok':correct(a),
                  'before_prediction':b['keys'][max(range(len(b['p'])),key=b['p'].__getitem__)],
                  'after_prediction':a['keys'][max(range(len(a['p'])),key=a['p'].__getitem__)]}
            paired.append(item)
            groups['all'].append(item)
            groups['source/'+a['source']].append(item)
            if key in tags:
                t=tags[key]
                groups[t['family']+'/mechanism/'+t['mechanism']].append(item)
                if t['family']=='ambiguous':groups['ambiguous/answer_status/'+t['tags']['answer_status']].append(item)
                if t['family']=='long_policy':groups['long_policy/payable/'+str(t['tags']['payable'])+'/'+key[1]].append(item)
        stats={}
        for g,rows in groups.items():
            n=len(rows);bc=sum(r['before_ok'] for r in rows);ac=sum(r['after_ok'] for r in rows)
            repair=sum(not r['before_ok'] and r['after_ok'] for r in rows)
            broken=sum(r['before_ok'] and not r['after_ok'] for r in rows)
            stats[g]={'n':n,'before_correct':bc,'after_correct':ac,'before_pct':100*bc/n,'after_pct':100*ac/n,
                      'delta_pp':100*(ac-bc)/n,'repaired':repair,'newly_wrong':broken,'original_errors':n-bc,
                      'repair_pct_of_original_errors':100*repair/(n-bc) if n!=bc else None}
        report=json.loads((run/'eval-hard-v1/report.json').read_text())
        results[model]={'metrics':stats,'training':json.loads((run/'stage4/training_metrics.json').read_text()),
                        'preflight':json.loads((run/'preflight.json').read_text()),'evaluation_coverage':report['coverage']}
    summary={'status':'complete','date':'2026-10-30','models':results,'input_hashes':inputs,
             'metric':'Per-question argmax accuracy; paired by id/question, identical gold and option keys.',
             'limitations':['Only hard-v1 evaluated; devtools tool-routing and prompt-injection subsets not evaluated here.',
               'Baseline predictions reused from original stage3, with scalar temperature calibration. Calibration affects probabilities but not argmax; do not compare NLL/ECE directly.',
               'One seed, one epoch, known diagnostic test. Not evidence of generalization or a controlled data-only ablation.']}
    (OUT/'comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (OUT/'paired_hard_v1.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in paired))
    with (OUT/'comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['model','group']+list(results['qwen3']['metrics']['all']))
        w.writeheader()
        for m,v in results.items():
            for g,s in v['metrics'].items():w.writerow({'model':m,'group':g,**s})
    lines=['# Kev v3 小样本一轮试训结果（2026-10-30）','',
           '两模型均从原stage3加载LoRA和pointer head，使用128条情境/154子题训练1 epoch，共16次优化更新；其中68条新情境、原三类各20条。没有接续v1/v2 stage4。',
           '', '| 模型 | 训练耗时（不含加载评测） | 读入/截断/拒绝 | hard-v1续训前 | 续训后 | 变化 | 修复旧错/新增错 |',
           '|---|---:|---|---:|---:|---:|---|']
    for m,v in results.items():
        s=v['metrics']['all'];t=v['training']
        lines.append(f"| {m} | {t['wall_seconds']:.2f}秒 | {t['records_seen']}/{t['truncated_records']}/{t['rejected_records']} | {s['before_pct']:.2f}% | {s['after_pct']:.2f}% | {s['delta_pp']:+.2f}pp | {s['repaired']}/{s['newly_wrong']} |")
    lines+=['','## 按题型逐题配对','', '| 题型 | 子题数 | Qwen3 前→后（答对题数） | 修复/新增错 | Qwen3.5 前→后 | 修复/新增错 |','|---|---:|---|---|---|---|']
    for g in results['qwen3']['metrics']:
        if not g.startswith('source/'):continue
        a=results['qwen3']['metrics'][g];b=results['qwen35']['metrics'][g]
        lines.append(f"| {g[7:]} | {a['n']} | {a['before_correct']}→{a['after_correct']} | {a['repaired']}/{a['newly_wrong']} | {b['before_correct']}→{b['after_correct']} | {b['repaired']}/{b['newly_wrong']} |")
    lines+=['','## 先前明显薄弱的子集','', '| 子集 | n | Qwen3 前→后 | Qwen3.5 前→后 |','|---|---:|---|---|']
    for g in ('ambiguous/answer_status/unknown','long_policy/payable/True/amount','long_policy/payable/False/amount','probability/mechanism/table:row_given_col'):
        if g not in results['qwen3']['metrics']:continue
        a=results['qwen3']['metrics'][g];b=results['qwen35']['metrics'][g]
        lines.append(f"| {g} | {a['n']} | {a['before_correct']}→{a['after_correct']} | {b['before_correct']}→{b['after_correct']} |")
    lines+=['','## 解释范围','',
        '统计基于同一hard-v1的1088道子题，按ID和question逐项对齐并核对标签、选项顺序。修复只统计原来答错而本次答对的题，新增错只统计相反方向。不同模型的原错题分母不同。',
        '原stage3结果来自既有预测快照，采用argmax准确率。原模型的标量温度校准不改变argmax，但本轮没有重做校准，因此不直接比较概率、NLL或ECE。',
        '本次只评hard-v1，没有重跑devtools，工具路由和提示注入的测试结果不能据此更新。hard-v1已参与设计分析，不是未见测试集。',
        '本轮还减少了训练数据量、取消6000条通用replay并关闭选项增强，因此不能把与v2的差异完全归因于新题质量。128条只训一轮，结果可用于决定是否扩大试验，不能证明稳定收益。',
        '', '完整配对见paired_hard_v1.jsonl；所有子组见comparison.csv / comparison.json。原始日志、配置、预测和报告位于evidence/；模型权重留在服务器的runs/qwen3-20261030-targeted-v3-pilot/stage4与runs/qwen35-20261030-targeted-v3-pilot/stage4。']
    (OUT/'试训结果.md').write_text('\n'.join(lines)+'\n')
    (OUT/'run_status.json').write_text(json.dumps({'status':'complete','date':'2026-10-30','training_and_hard_v1_complete':True,
        'remote_root':'/C20545/kev-08b-official-repro-20261026', 'run_names':['qwen3-20261030-targeted-v3-pilot','qwen35-20261030-targeted-v3-pilot'],
        'models':{m:v['metrics']['all'] for m,v in results.items()}},ensure_ascii=False,indent=2)+'\n')
    print((OUT/'试训结果.md').read_text())


if __name__=='__main__':main()
