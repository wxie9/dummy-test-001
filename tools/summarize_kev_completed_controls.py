#!/usr/bin/env python3
"""Generate the comparison from completed per-control evidence summaries."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'artifacts/kev_training_eval_20261026'
DIRS={'v5_1ep':'targeted_v5_20261030','guard_1ep':'targeted_v5_none_guard_candidate_20261030','v5_3ep':'targeted_v5_3ep_20261030'}
NAMES={'tool_routing':'工具路由','temporal':'时间与数值','probability':'概率','insufficient':'信息不足','multihop':'多跳','policy':'长政策','injection':'提示注入'}


def main():
    data={k:json.loads((ROOT/d/'comparison-seven.json').read_text()) for k,d in DIRS.items()}
    result={'controls':data,'goal_achieved':False,'scope':'Single-seed comparisons on inspected diagnostic data. No all-seven improvement, no independent generalization claim.'}
    lines=['# Kev v5 两组完整对照结果','',
        '两组对照均已完成。修复重复“以上皆非”监督后，没有出现两模型七类全面改善；同一数据从一轮增加到三轮，也没有解决多跳和长政策的下降。下一轮优先改数据覆盖与问法，保留正确的增强保护，不再只增加训练轮数。','',
        '所有实验均从续训前的原stage3开始，使用1500个定向训练情境和6000条旧数据回放。共同设置为seed101、lr1e-5、LoRA16、batch4、梯度累积2。增强修复只保护90道自带“以上皆非”的多跳题；一轮938次更新，三轮2814次更新。两个对照的训练前开发/探针预测均精确复现v5起点，概率差为0。','']
    for model,title in [('qwen3','Qwen3-0.6B'),('qwen35','Qwen3.5-0.8B')]:
        lines += [title+'：下表是正确题数，分母固定。','',
            '|类别|题数|续训前|v5一轮|增强修复一轮|v5三轮|','|---|---:|---:|---:|---:|---:|']
        for family,label in NAMES.items():
            vals=[d['models'][model]['seven_categories'][family] for d in data.values()]
            assert len({(v['questions'],v['before_correct']) for v in vals})==1
            lines.append(f"|{label}|{vals[0]['questions']}|{vals[0]['before_correct']}|"+'|'.join(str(v['after_correct']) for v in vals)+'|')
        vals=[d['models'][model]['seven_pooled'] for d in data.values()]
        lines.append(f"|七类合计|1000|{vals[0]['before_correct']}|"+'|'.join(str(v['after_correct']) for v in vals)+'|')
        lines.append('')
    lines += ['三轮修复了更多原先的错题，但也新增了更多错误。以下都相对原stage3计算，未把一轮结果当成“续训前”。','',
              '|模型|条件|修复原错题|原对题变错|净增加正确数|','|---|---|---:|---:|---:|']
    for model in ['qwen3','qwen35']:
        for key,label in [('guard_1ep','增强修复一轮'),('v5_3ep','v5三轮')]:
            s=data[key]['models'][model]['seven_pooled']
            lines.append(f"|{model}|{label}|{s['repaired']}|{s['newly_wrong']}|{s['after_correct']-s['before_correct']:+d}|")
    lines += ['',
        '多跳的训练样本表现提高，真实题却没有跟着提高。固定20题训练探针从v5一轮到三轮，Qwen3为7→15，Qwen3.5为11→17；开发集也从17→29/60、29→38/60提高。真实多跳则分别57→57/125、85→83/125。继续增加同一种合成题的训练次数，不能代替补齐缺少的题型。',
        '',
        '长政策的主要短板仍是实际赔付。三轮相对原stage3，35道正金额题的金额答案Qwen3从16降到13，Qwen3.5从17降到14；对应处理结果从8降到6、8降到7。65道零金额题一直全部答对，因此总准确率会掩盖正金额题的困难。',
        '',
        '信息不足也存在取舍。三轮中，事实足够的61题Qwen3从30到34、Qwen3.5从35到39；真正未知的39题却从36到33、34到32。开发集缺事实配对明显提高，仍不能代替真实未知题的保持。',
        '',
        '接下来保持1500个情境：概率350、多跳270、信息不足280、长政策300，以及原工具/时间/注入各100。概率候选已补齐概率区间和金额量级；多跳候选补主管跳数、按日期值班表、控制权与经济权益；信息不足候选增加等价决策表达和事实是否支持结论的监督；政策需把通用原因标签改写成清楚的处理结果，并检查配对选项。新增子问题不计作新增独立情境。先完成组合后的题面、标签、增强及长度检查，再从原stage3开新实验。',
        '',
        '当前这四路训练与评测均已结束，没有保留后台训练等待重启。原三类题面未修改，日期措辞澄清仍未收到回答。已有检查发现的歧义不因此被视作解决。',
        '',
        '这些数据集已用于错误分析；结果只有一个训练随机种子。各类置信区间与逐题修复记录保存在各目录JSON/CSV中，区间未作14项多重比较校正。本记录不宣称独立泛化，也不从不同实验逐类挑最高成绩拼成一个模型。','',
        '证据已下载并逐文件核验：增强修复归档83个被索引文件；三轮归档92个。归档还包含原始预测、覆盖报告、训练配置、实际训练代码和checkpoint文件哈希；模型权重保留在服务器。','']
    for k,d in DIRS.items():
        lines.append(f'- `{d}/comparison-seven.json`、`七类结果.md`、`paired-seven.jsonl`、`train_probe_comparison.json`。')
    lines += ['','复算程序：`tools/summarize_kev_completed_controls.py`；单组证据收集：`tools/collect_kev_control_evidence.py`。']
    (ROOT/'v5_control_comparison_20261030.md').write_text('\n'.join(lines)+'\n')
    result['source_summary_hashes']={d:hashlib.sha256((ROOT/d/'comparison-seven.json').read_bytes()).hexdigest() for d in DIRS.values()}
    (ROOT/'v5_control_comparison_20261030.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Wrote combined comparison; goal remains unachieved.')


if __name__=='__main__':main()
