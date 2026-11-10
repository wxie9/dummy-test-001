#!/usr/bin/env python3
"""Strict seven-family paired comparison; refuse incomplete/mismatched evidence."""
import argparse,csv,hashlib,json,random
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/kev_training_eval_20261026/targeted_v4_20261030'
TARGETS={
 'tool_routing':('devtools-v1','when2call','action'),
 'temporal':('hard-v1','hard_temporal_numeric',None),
 'probability':('hard-v1','hard_probability',None),
 'insufficient':('hard-v1','hard_ambiguous',None),
 'multihop':('hard-v1','hard_multi_hop',None),
 'policy':('hard-v1','hard_long_policy',None),
 'injection':('devtools-v1','prompt_injection','injection')}

def load(p):return json.loads(p.read_text())
def correct(r):return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']
def paired(before,after):
    # The frozen devtools source has a repeated codereviewer id. Both readers
    # preserve the frozen input order; retain both occurrences instead of silently
    # collapsing one. Reject any reordered stream rather than guess its mapping.
    assert [(r['id'],r['question']) for r in before]==[(r['id'],r['question']) for r in after]
    def index(rows):
        counts=Counter();out={}
        for r in rows:
            k=(r['id'],r['question']);counts[k]+=1;out[(*k,counts[k])]=r
        return out
    b=index(before);a=index(after)
    assert len(b)==len(before) and len(a)==len(after) and a.keys()==b.keys()
    out=[]
    for key,x in b.items():
        y=a[key]
        assert x['keys']==y['keys'] and x['label']==y['label'] and x['source']==y['source']
        out.append({'id':key[0],'question':key[1],'occurrence':key[2],'source':x['source'],'before_ok':correct(x),'after_ok':correct(y),
                    'before_answer':x['keys'][max(range(len(x['p'])),key=x['p'].__getitem__)],
                    'after_answer':y['keys'][max(range(len(y['p'])),key=y['p'].__getitem__)]})
    return out

def stats(rows):
    assert rows
    n=len(rows);before=sum(r['before_ok'] for r in rows);after=sum(r['after_ok'] for r in rows)
    fixed=sum(not r['before_ok'] and r['after_ok'] for r in rows);broken=sum(r['before_ok'] and not r['after_ok'] for r in rows)
    groups=defaultdict(list)
    for r in rows:groups[r['id']].append(int(r['after_ok'])-int(r['before_ok']))
    clusters=[(sum(v),len(v)) for v in groups.values()]
    rng=random.Random(20261030);boot=[]
    for _ in range(2000):
        sample=rng.choices(clusters,k=len(clusters))
        boot.append(100*sum(a for a,b in sample)/sum(b for a,b in sample))
    boot.sort()
    return {'questions':n,'contexts':len(clusters),'before_correct':before,'after_correct':after,
            'before_pct':100*before/n,'after_pct':100*after/n,'delta_pp':100*(after-before)/n,
            'repaired':fixed,'newly_wrong':broken,'old_wrong':n-before,
            'repair_pct':100*fixed/(n-before) if before<n else None,
            'paired_context_bootstrap_95pct_pp':[boot[50],boot[1949]]}

def main():
    global OUT
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-dir',type=Path,default=OUT)
    ap.add_argument('--evidence',type=Path)
    ap.add_argument('--run-version',choices=['v4','v5','v5-3ep','v5-guard','v6','v6-3ep','v6-factmix','v7','v7-lr5','v8-steps','v9-matched'],default='v4')
    a=ap.parse_args();OUT=a.data_dir
    if a.evidence is None:a.evidence=OUT/'evidence'
    results={};allpairs=[];hashes={}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        new=a.evidence/'runs'/f'{model}-20261030-targeted-{a.run_version}'
        assert (new/'status.txt').read_text().strip()=='complete'
        suites={};summary={}
        for suite in ('hard-v1','devtools-v1'):
            old=a.evidence/'runs'/original/'benchmarks'/f'{suite}-test'
            current=new/f'eval-{suite}'
            br,ar=load(old/'report.json'),load(current/'report.json')
            assert br['suite_sha256']==ar['suite_sha256']
            for report in (br,ar):
                coverage=report['coverage'];assert coverage['rejected_records']==coverage['truncated_records']==0
                assert coverage['evaluated_questions']==coverage['requested_questions']
            suites[suite]=paired(load(old/'rows.json'),load(current/'rows.json'))
            summary[suite]=stats(suites[suite])
            for directory in (old,current):
                p=directory/'rows.json';hashes[str(p.relative_to(a.evidence))]=hashlib.sha256(p.read_bytes()).hexdigest()
            allpairs.extend({'model':model,'suite':suite,**r} for r in suites[suite])
        targets={};target_rows=[]
        for family,(suite,source,question) in TARGETS.items():
            rows=[r for r in suites[suite] if r['source']==source and (question is None or r['question']==question)]
            targets[family]=stats(rows)
            target_rows.extend(rows)
        assert len(target_rows)==1000
        dev=paired(load(new/'development-before/rows.json'),load(new/'development-after/rows.json'))
        metadata={r['_meta']['id']:r['_meta'] for r in map(json.loads,(OUT/'development.jsonl').read_text().splitlines())}
        family_map={rid:m['family'] for rid,m in metadata.items()}
        dev_by_family={family:stats([{**r,'id':metadata[r['id']].get('group_id',r['id'])} if a.run_version=='v9-matched' else r for r in dev if family_map[r['id']]==family]) for family in TARGETS}
        if a.run_version=='v9-matched':dev=[{**r,'id':metadata[r['id']].get('group_id',r['id'])} for r in dev]
        results[model]={'seven_categories':targets,'suite_overall':summary,'development':{'all':stats(dev),'by_family':dev_by_family},
            'seven_pooled':stats(target_rows),
            'macro_delta_pp':sum(s['delta_pp'] for s in targets.values())/7,
            'minimum_category_delta_pp':min(s['delta_pp'] for s in targets.values()),
            'training':load(new/'stage4/training_metrics.json')}
    report={'models':results,'evidence_hashes':hashes,'goal_achieved':False,
            'scope':'Single-seed inspected diagnostic evaluation. All seven categories must be assessed; no completion claim from a positive average alone.',
            'interval_note':'Paired context bootstrap on the fixed diagnostic item distribution; not training-seed uncertainty or independent-generalization evidence. Intervals are unadjusted across 14 model/category comparisons.'}
    (OUT/'comparison-seven.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'paired-seven.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in allpairs))
    with (OUT/'comparison-seven.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['model','category']+list(results['qwen3']['seven_categories']['tool_routing']))
        w.writeheader()
        for model,result in results.items():
            for category,value in result['seven_categories'].items():w.writerow({'model':model,'category':category,**value})
    lines=[f'# Kev {a.run_version} 七类配对结果','', '| 类别 | 题数 | Qwen3 前→后 | 变化pp | 修复/新增错 | Qwen3.5 前→后 | 变化pp | 修复/新增错 |','|---|---:|---|---:|---|---|---:|---|']
    for family in TARGETS:
        b=results['qwen3']['seven_categories'][family];c=results['qwen35']['seven_categories'][family]
        lines.append(f"| {family} | {b['questions']} | {b['before_pct']:.2f}%→{b['after_pct']:.2f}% | {b['delta_pp']:+.2f} | {b['repaired']}/{b['newly_wrong']} | {c['before_pct']:.2f}%→{c['after_pct']:.2f}% | {c['delta_pp']:+.2f} | {c['repaired']}/{c['newly_wrong']} |")
    training_args=load(a.evidence/'runs'/f'qwen3-20261030-targeted-{a.run_version}'/'stage4/training_config.json')['args']
    epoch_count=training_args['epochs'];learning_rate=training_args['lr']
    data_description='1500基础情境+1020额外配对视图+6000回放' if a.run_version=='v9-matched' else '1500定向情境+6000回放'
    lines+=['',f'训练从原stage3开始，{data_description}，{epoch_count}epoch，学习率{learning_rate:g}。开发集与训练集共生成规则，hard-v1已用于错误分析；本结果不能单独证明独立泛化或多种子稳定提升。Bootstrap区间见JSON/CSV，按基础情境成组重采样，未作14项多重比较校正。',
            'devtools原始测试有两条codereviewer/cls-test/19245同ID记录，已按冻结数据顺序保留并用出现序号配对，未去重删除。前后完整ID序列、标签和选项顺序核对一致；该重复不在七类目标子集中。']
    (OUT/'七类结果.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
