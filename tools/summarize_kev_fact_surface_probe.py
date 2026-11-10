#!/usr/bin/env python3
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/kev_training_eval_20261026/fact_surface_probe_20261030'
V6=OUT.with_name('targeted_v6_20261030')
CONDITIONS=['original','without_warning','prose','prose_without_warning']

def load(p):return json.loads(p.read_text())
def ok(r):return max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']

def main():
    data=[json.loads(l) for l in (OUT/'probe.jsonl').read_text().splitlines()]
    meta={r['_meta']['id']:r['_meta'] for r in data}
    digest=hashlib.sha256((OUT/'probe.jsonl').read_bytes()).hexdigest()
    output={'models':{},'data_sha256':digest,
        'scope':'30 synthetic development contexts in four framing conditions. All five original questions preserved. Same cases are reused, not 120 independent cases; only 12 parents contain the warning. No best-wording selection per item.'}
    native_root=V6/'evidence/runs'
    lines=['# 事实表达方式对照','','30个相同开发情境，保留全部事实、规则、5个问题和选项；只改事实写法或删除不提供事实的提示语。下表是主决策问的正确数，每格分母30。','','|模型/权重|原文|去提示语|句子表达|句子表达且去提示语|','|---|---:|---:|---:|---:|']
    for model in ['qwen3','qwen35']:
        assert (OUT/(model+'.status')).read_text().strip()=='complete'
        output['models'][model]={}
        for checkpoint,side in [('stage3','before'),('v6','after')]:
            folder=OUT/(model+'_'+checkpoint);report=load(folder/'report.json');rows=load(folder/'rows.json')
            c=report['coverage'];assert c['evaluated_records']==c['requested_records']==120
            assert c['evaluated_questions']==c['requested_questions']==len(rows)==600
            assert c['rejected_records']==c['truncated_records']==0
            assert report['data_sha256']==digest
            native=load(native_root/(model+'-20261030-targeted-v6')/('development-'+side)/'rows.json')
            native={(r['id'],r['question']):r for r in native}
            controls=[r for r in rows if meta[r['id']]['probe_condition']=='original']
            assert len(controls)==150
            for r in controls:
                old=native[(meta[r['id']]['probe_parent_id'],r['question'])]
                assert (r['keys'],r['label'])==(old['keys'],old['label'])
                assert r['p']==old['p'],'Control probabilities fail exact reproduction'
            index={(meta[r['id']]['probe_parent_id'],meta[r['id']]['probe_condition'],r['question']):r for r in rows}
            variants={}
            for mode in CONDITIONS:
                group=[r for r in rows if meta[r['id']]['probe_condition']==mode]
                parts=defaultdict(list)
                for r in group:
                    m=meta[r['id']];parts['question/'+r['question']].append(r)
                    if r['question']=='decision':
                        parts['scenario/'+m['subtype'].split('__')[0]].append(r)
                        role='unknown' if m['pair_role']=='missing_deciding' else 'determinate'
                        parts['information/'+role].append(r)
                        parts['warning_present/'+str(m['original_has_warning'])].append(r)
                stats={key:{'n':len(rs),'correct':sum(ok(r) for r in rs)} for key,rs in parts.items()}
                changed=[]
                for r in group:
                    parent=meta[r['id']]['probe_parent_id'];before=index[(parent,'original',r['question'])]
                    if ok(before)!=ok(r):changed.append({'parent':parent,'question':r['question'],'before_ok':ok(before),'after_ok':ok(r)})
                variants[mode]={'scores':stats,'changes_vs_original':changed}
            output['models'][model][checkpoint]={'original_control_exactly_reproduced':150,'conditions':variants}
            counts=[str(variants[m]['scores']['question/decision']['correct']) for m in CONDITIONS]
            lines.append('|'+model+'/'+checkpoint+'|'+'|'.join(counts)+'|')
    (OUT/'comparison.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    lines+=['','四套权重条件的原文对照均逐值复现此前开发集概率（各150个子问）。不是新分布准确率，不从四种表达中按题挑最优答案。子类和所有变化见comparison.json。']
    (OUT/'结果.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
