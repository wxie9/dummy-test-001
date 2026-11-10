#!/usr/bin/env python3
"""Compare two completed controls on the same frozen test occurrences."""
import argparse
import hashlib
import json
from pathlib import Path
from summarize_targeted_v4 import TARGETS, stats


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--reference-dir',type=Path,required=True);ap.add_argument('--candidate-dir',type=Path,required=True)
    ap.add_argument('--output-stem',default='relative_to_v5_one_epoch')
    a=ap.parse_args()
    assert Path(a.output_stem).name==a.output_stem
    paths=[d/'paired-seven.jsonl' for d in [a.reference_dir,a.candidate_dir]]
    before,after=[[json.loads(l) for l in p.read_text().splitlines()] for p in paths]
    key=lambda r:tuple(r[k] for k in ['model','suite','id','question','occurrence','source'])
    assert list(map(key,before))==list(map(key,after))
    paired=[]
    for x,y in zip(before,after):
        assert x['before_ok']==y['before_ok'] and x['before_answer']==y['before_answer']
        paired.append({**y,'before_ok':x['after_ok'],'before_answer':x['after_answer'],'original_stage3_ok':x['before_ok']})
    result={'reference':a.reference_dir.name,'candidate':a.candidate_dir.name,
            'source_pair_file_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'models':{},
            'scope':'Direct comparison of single-seed controls on an already-inspected diagnostic set. Not an independent generalization or multi-seed result.'}
    lines=[f'# 与 {a.reference_dir.name} 的直接对照','','|模型|类别|参考正确数|本轮正确数|变化pp|修复/新增错（相对参考）|','|---|---|---:|---:|---:|---|']
    for model in ['qwen3','qwen35']:
        families={};pool=[]
        for family,(suite,source,question) in TARGETS.items():
            rows=[r for r in paired if r['model']==model and r['suite']==suite and r['source']==source and (question is None or question==r['question'])]
            s=stats(rows);pool.extend(rows)
            s['original_stage3_wrong_count']=sum(not r['original_stage3_ok'] for r in rows)
            s['reference_repairs_of_original_errors']=sum(not r['original_stage3_ok'] and r['before_ok'] for r in rows)
            s['candidate_repairs_of_original_errors']=sum(not r['original_stage3_ok'] and r['after_ok'] for r in rows)
            families[family]=s
            lines.append(f"|{model}|{family}|{s['before_correct']}/{s['questions']}|{s['after_correct']}/{s['questions']}|{s['delta_pp']:+.2f}|{s['repaired']}/{s['newly_wrong']}|")
        assert len(pool)==1000
        result['models'][model]={'seven_categories':families,'seven_pooled':stats(pool)}
    (a.candidate_dir/(a.output_stem+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    markdown_name='与v5一轮对照.md' if a.output_stem=='relative_to_v5_one_epoch' else a.output_stem+'.md'
    (a.candidate_dir/markdown_name).write_text('\n'.join(lines)+'\n\n'+result['scope']+'\n')
    print('\n'.join(lines))


if __name__=='__main__':main()
