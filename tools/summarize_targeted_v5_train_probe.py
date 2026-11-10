#!/usr/bin/env python3
"""Separate training-set acquisition from same-generator development transfer."""
import json
import argparse
import hashlib
from pathlib import Path
from build_targeted_v5 import OUT
from summarize_targeted_v4 import paired, stats

def main():
    global OUT
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,default=OUT);ap.add_argument('--run-version',choices=['v5','v5-3ep','v5-guard','v6','v6-3ep','v6-factmix','v7','v7-lr5','v8-steps','v9-matched'],default='v5')
    a=ap.parse_args();OUT=a.data_dir
    data=OUT/'train_probe.jsonl'
    expected_hash=hashlib.sha256(data.read_bytes()).hexdigest()
    metadata={r['_meta']['id']:r['_meta'] for r in map(json.loads,data.read_text().splitlines())}
    expected_questions=sum(len(r['questions']) for r in map(json.loads,data.read_text().splitlines()))
    assert len(metadata)==140
    result={}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        root=OUT/'evidence/runs'/f'{model}-20261030-targeted-{a.run_version}'
        loaded=[]
        for split,checkpoint in [('before',f'{original}/stage3'),('after',f'{model}-20261030-targeted-{a.run_version}/stage4')]:
            folder=root/('train-probe-'+split)
            report=json.loads((folder/'report.json').read_text())
            assert report['data_sha256']==expected_hash and report['run'].endswith('/'+checkpoint)
            c=report['coverage']
            assert c['requested_records']==c['evaluated_records']==140
            assert c['requested_questions']==c['evaluated_questions']==expected_questions
            assert c['rejected_records']==c['truncated_records']==0
            loaded.append(json.loads((folder/'rows.json').read_text()))
        pairs=paired(*loaded)
        result[model]={'overall':stats(pairs),'families':{f:stats([r for r in pairs if metadata[r['id']]['family']==f]) for f in sorted({m['family'] for m in metadata.values()})}}
        result[model]['family_question']={f+'/'+q:stats([r for r in pairs if metadata[r['id']]['family']==f and r['question']==q]) for f,q in sorted({(metadata[r['id']]['family'],r['question']) for r in pairs})}
    report={'models':result,'data_sha256':expected_hash,'scope':'Fixed 20 contexts per family drawn from the training corpus before completion. These are in-sample scores, not generalization results.'}
    (OUT/'train_probe_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for model,res in result.items():
        for family,s in res['families'].items():print(model,family,f"{s['before_correct']}->{s['after_correct']}/{s['questions']}")

if __name__=='__main__':main()
