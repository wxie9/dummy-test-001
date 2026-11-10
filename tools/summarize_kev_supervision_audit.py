#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'supervision_weight_audit_20261030'
V6=BASE/'targeted_v6_20261030'

def read(p):return json.loads(p.read_text())

def main():
    a,b=[read(OUT/(name+'.json'))['epochs'][0] for name in ['v5_guard','v6']]
    i=b['families']['insufficient']['actual_ce_mass']
    direct=sum(v['actual_ce_mass'] for k,v in b['questions'].items() if k.startswith('insufficient/decision'))
    dep=[v['subtypes']['multihop/dependency_candidates']['actual_ce_mass'] for v in [a,b]]
    confusion={}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        results={}
        for side,path in [('before',V6/'evidence/runs'/original/'benchmarks/hard-v1-test/rows.json'),
                          ('after',V6/'evidence/runs'/(model+'-20261030-targeted-v6')/'eval-hard-v1/rows.json')]:
            counts=Counter()
            for r in read(path):
                if r['source']!='hard_ambiguous':continue
                predicted=r['keys'][max(range(len(r['p'])),key=r['p'].__getitem__)]
                gold=r['keys'][r['label']]
                known=gold!='cannot_be_determined'
                counts['questions']+=1
                counts['predicted_unknown']+=predicted=='cannot_be_determined'
                counts['known_but_predicted_unknown']+=known and predicted=='cannot_be_determined'
                counts['known_correct']+=known and predicted==gold
                counts['unknown_correct']+=not known and predicted==gold
            results[side]=dict(counts)
        confusion[model]=results
    summary={'real_insufficient':confusion,'epoch0_exposure':{
        'v5_guard_insufficient_total':a['families']['insufficient']['actual_ce_mass'],
        'v6_insufficient_total':i,'v6_direct_decision_share':direct/i,'v6_auxiliary_share':1-direct/i,
        'dependency_v5_guard':dep[0],'dependency_v6':dep[1],'dependency_ratio':dep[1]/dep[0]},
        'scope':'Exposure means summed scalar cross-entropy coefficients before optimizer/clipping/learning-rate scaling; not gradient norms or demonstrated causes of accuracy changes.'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['# Kev v6 监督权重与信息不足错误检查','',
        '本检查不修改数据或训练代码。三轮对照继续保持原配置。上一轮新增错误与权重变化均是诊断证据，不能直接当成下降原因。','',
        '## 真实信息不足题','',
        '|模型|续训前误判未知的已知题|续训后|未知题正确数前→后|','|---|---:|---:|---:|']
    for model,x in confusion.items():
        old,new=x['before'],x['after']
        lines.append(f"|{model}|{old['known_but_predicted_unknown']}/61|{new['known_but_predicted_unknown']}/61|{old['unknown_correct']}→{new['unknown_correct']}/39|")
    lines+=['','Qwen3新增的7个信息不足类错误均改答“无法判断”：3个运费题、3个退货日期题、1个工时题，所需数字和日期已给全。','',
        '## 实际监督权重','',
        f'按实际随机种子、每批4条、累积2批、6000条固定回放及选项增强重放第0轮，信息不足类总CE系数为{a["families"]["insufficient"]["actual_ce_mass"]:.3f}→{i:.3f}，总量基本相同。v6三个等价决策问法合计占该类{100*direct/i:.2f}%，两个证据充分性辅助问占{100*(1-direct/i):.2f}%。因此不能把5个子问解释成5倍原决策监督；也不能只看单个原问法的份额，忽略另外两个等价问法。',
        f'依赖传播情境从90减到45，实际CE系数从{dep[0]:.3f}到{dep[1]:.3f}，约为原来的{100*dep[1]/dep[0]:.2f}%。新多跳类型的加入挤占了这一子类的训练次数。它与依赖题退步同时发生，但不构成单因素因果证明。','',
        '另一个实现细节：训练器先对每个增强版本中的问题取均值，再对批内所有版本统一归一化。当4个原情境分别生成3、1、1、1个版本时，实际源情境梯度系数为1/4、1/12、1/12、1/12，第一条是其余的3倍，并非批内原情境等权。已直接调用服务器batch_loss，以相同两类logit验证得到2.99999991的比例。只有整体批次均值被归一化；增强版本较多的原情境仍获得更多相对权重。','',
        '这不自动意味着应改训练器；需要单独对照验证。当前运行的实验没有修改此行为。','',
        '## 事实表达方式对照','',
        '另有30个开发情境的四种表达对照，保留全部事实、规则、问题、选项和答案。Qwen3原stage3的原文/句子表达为13/14题正确；v6为17/13题。Qwen3.5分别17/16、18/19。删除提示语本身没有改变v6主决策正确数。说明Qwen3在这组题上的收益对事实写法敏感，不能用Qwen3.5的表现概括两模型。','',
        '原文对照各150个子问均逐值复现原开发概率；30情境包含相关配对，不是120个独立样本。此检查只涉及退货、运费、工时，不能推广为七类的统一解释。详见相邻fact_surface_probe_20261030目录。','',
        '证据：v5_guard.json、v6.json、coefficient_gradient_check.json、summary.json。审计代码tools/audit_kev_loss_exposure.py；复算tools/summarize_kev_supervision_audit.py。']
    (OUT/'说明.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
