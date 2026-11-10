#!/usr/bin/env python3
"""Summarize complete training-set acquisition, separately from official tests."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from summarize_targeted_v4 import paired
from diagnose_kev_v7_development import axes

def counts(rows):
    n=len(rows);before=sum(r['before_ok'] for r in rows);after=sum(r['after_ok'] for r in rows)
    return {'questions':n,'contexts':len({r['id'] for r in rows}),'before_correct':before,'after_correct':after,'before_pct':100*before/n,'after_pct':100*after/n,'delta_pp':100*(after-before)/n,'repaired':sum(not r['before_ok'] and r['after_ok'] for r in rows),'newly_wrong':sum(r['before_ok'] and not r['after_ok'] for r in rows)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);a=ap.parse_args();p=a.directory.resolve();e=p/'evidence'/p.name
    raw=[json.loads(l) for l in (p/'train_eval.jsonl').read_text().splitlines()];byid={r['_meta']['id']:r for r in raw};assert len(raw)==1500
    report={'scope':'All 1500 training contexts / 2320 questions, no augmentation. This measures training acquisition, not generalization; official results are reported separately.','models':{}}
    lines=['# 完整训练集掌握情况','', '以下为1,500道训练情境上的表现，不是独立评测成绩。','', '|模型|类别|训练前正确|训练后正确|题数|变化pp|','|---|---|---:|---:|---:|---:|']
    for model in ['qwen3','qwen35']:
        before=json.loads((e/(model+'-stage3')/'rows.json').read_text());after=json.loads((e/(model+'-v7')/'rows.json').read_text());pairs=paired(before,after);assert len(pairs)==2320
        groups=defaultdict(list);contexts=defaultdict(list)
        for r in pairs:
            raw_r=byid[r['id']];contexts[(raw_r['_meta']['family'],r['id'])].append(r)
            for axis,value in axes(raw_r,r['question']):groups[(axis,value)].append(r)
        subgroups=[{'axis':axis,'value':value,**counts(rs)} for (axis,value),rs in sorted(groups.items())]
        family={g['value']:{k:v for k,v in g.items() if k not in ['axis','value']} for g in subgroups if g['axis']=='family'}
        whole=defaultdict(list)
        for (f,rid),rs in contexts.items():whole[f].append({'id':rid,'before_ok':all(r['before_ok'] for r in rs),'after_ok':all(r['after_ok'] for r in rs)})
        report['models'][model]={'overall':counts(pairs),'families':family,'whole_context':{f:counts(rs) for f,rs in whole.items()},'subgroups':subgroups}
        for f,s in family.items():lines.append(f'|{model}|{f}|{s["before_correct"]}|{s["after_correct"]}|{s["questions"]}|{s["delta_pp"]:+.2f}|')
    (p/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(p/'训练集结果.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':main()
