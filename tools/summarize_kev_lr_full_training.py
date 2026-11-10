#!/usr/bin/env python3
"""Compare stage3, v7 and v7-lr5 on the exact complete training corpus."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from summarize_targeted_v4 import paired
from summarize_kev_training_fit_audit import counts
from diagnose_kev_v7_development import axes

def summarize(raw, before, after):
    expected=[(r['_meta']['id'],qid) for r in raw for qid in r['questions']]
    assert len({r['_meta']['id'] for r in raw})==len(raw)
    assert [(r['id'],r['question']) for r in before]==expected
    assert [(r['id'],r['question']) for r in after]==expected
    byid={r['_meta']['id']:r for r in raw}
    pairs=paired(before,after)
    groups=defaultdict(list); contexts=defaultdict(list)
    for row in pairs:
        record=byid[row['id']]
        contexts[(record['_meta']['family'],row['id'])].append(row)
        for axis,value in axes(record,row['question']):groups[(axis,value)].append(row)
    subgroups=[{'axis':axis,'value':value,**counts(rows)} for (axis,value),rows in sorted(groups.items())]
    families={g['value']:{k:v for k,v in g.items() if k not in ['axis','value']} for g in subgroups if g['axis']=='family'}
    whole=defaultdict(list)
    for (family,rid),rows in contexts.items():
        whole[family].append({'id':rid,'before_ok':all(r['before_ok'] for r in rows),'after_ok':all(r['after_ok'] for r in rows)})
    return {'overall':counts(pairs),'families':families,'whole_context':{f:counts(rows) for f,rows in whole.items()},'subgroups':subgroups}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--version',choices=['v7-lr5','v8-steps'],default='v7-lr5');a=ap.parse_args();p=a.directory.resolve();e=p/'evidence'
    data=p/('train_original.jsonl' if a.version=='v8-steps' else 'train.jsonl')
    raw=[json.loads(l) for l in data.read_text().splitlines()];assert len(raw)==1500
    report={'scope':f'Fixed full training corpus, original questions only, not heldout performance. Compare original stage3, v7 lr1e-5, and {a.version}. Subgroups overlap and are diagnostic; no significance claim.', 'data_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'models':{}}
    for model in ['qwen3','qwen35']:
        fit=e/'v7_training_fit_audit_20261030';base=json.loads((fit/(model+'-stage3')/'rows.json').read_text());old=json.loads((fit/(model+'-v7')/'rows.json').read_text());new=json.loads((e/'runs'/(model+'-20261030-targeted-'+a.version)/'full-train-after/rows.json').read_text())
        by_reference={}
        for name,before in [('stage3',base),('v7',old)]:
            by_reference[name]=summarize(raw,before,new)
            assert by_reference[name]['overall']['questions']==2320
        report['models'][model]=by_reference
    (p/'full_training_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    for model,m in report['models'].items():
        for family,s in sorted(m['v7']['families'].items()):print(model,family,f"{s['before_correct']}->{s['after_correct']}/{s['questions']}")

if __name__=='__main__':main()
