#!/usr/bin/env python3
"""Evaluate base cases and strict matched-pair success separately."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from summarize_targeted_v4 import paired, stats


def summarize(data, before, after, pair_map):
    metadata={r['_meta']['id']:r['_meta'] for r in data}
    expected=[(r['_meta']['id'],qid) for r in data for qid in r['questions']]
    assert [(r['id'],r['question']) for r in before]==expected
    rows=paired(before,after)
    contexts=defaultdict(list)
    families=defaultdict(list)
    base=defaultdict(list)
    subgroups=defaultdict(list)
    for r in rows:
        m=metadata[r['id']];contexts[r['id']].append(r)
        # Bootstrap matched siblings together, never as independent records.
        item={**r,'id':m.get('group_id',r['id'])}
        families[m['family']].append(item)
        if m.get('view_role','base')=='base':base[m['family']].append(item)
        subgroups[m['family']+'/'+m.get('parent_stratum',m.get('subtype','unspecified'))+'/'+r['question']].append(item)
    joint=defaultdict(list)
    for p in pair_map:
        a,b=contexts[p['base_id']],contexts[p['matched_id']]
        assert a and b and {r['question'] for r in a}=={r['question'] for r in b}
        items=a+b
        item={'id':p['group_id'],'before_ok':all(r['before_ok'] for r in items),'after_ok':all(r['after_ok'] for r in items)}
        joint[p['family']].append(item)
        joint[p['family']+'/'+p['mutation']].append(item)
    return {'all_views_by_family':{k:stats(v) for k,v in families.items()},'base_only_by_family':{k:stats(v) for k,v in base.items()},'subgroups':{k:stats(v) for k,v in subgroups.items()},'strict_both_views_all_questions':{k:stats(v) for k,v in joint.items()}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);args=ap.parse_args();p=args.directory
    pair_map=json.loads((p/'pair_mapping.json').read_text());result={}
    for model in ['qwen3','qwen35']:
        run=p/'evidence/runs'/(model+'-20261030-targeted-v9-matched')
        assert (run/'status.txt').read_text().strip()=='complete'
        result[model]={}
        for kind,split in [('full-train','train'),('development','development')]:
            f=p/(split+'.jsonl');data=[json.loads(l) for l in f.read_text().splitlines()];digest=hashlib.sha256(f.read_bytes()).hexdigest()
            predictions=[]
            for when in ['before','after']:
                d=run/(kind+'-'+when);report=json.loads((d/'report.json').read_text());c=report['coverage']
                assert report['data_sha256']==digest
                assert c['requested_records']==c['evaluated_records']==len(data) and c['rejected_records']==c['truncated_records']==0
                predictions.append(json.loads((d/'rows.json').read_text()))
            result[model][split]=summarize(data,*predictions,pair_map[split])
    out={'models':result,'scope':'Training cases are in-sample. Development shares generators, with policy combinations reserved and extra graph side branches. Paired views share one bootstrap cluster. Strict pair success requires every question in both views correct. Single seed; no causal attribution among content, exposure and augmentation changes.'}
    (p/'matched_training_diagnostics.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({m:{s:r['strict_both_views_all_questions'] for s,r in v.items()} for m,v in result.items()},ensure_ascii=False))


if __name__=='__main__':main()
