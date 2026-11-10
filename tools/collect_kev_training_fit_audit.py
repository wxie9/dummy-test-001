#!/usr/bin/env python3
"""Verify and archive four completed full-corpus inference runs."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path
from datetime import datetime, timezone

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();root=a.root.resolve();data=root/'v7_training_fit_audit_20261030';v7=root/'targeted_v7_20261030';m=read(data/'manifest.json')
    statuses={name:(data/(name+'.status.txt')).read_text().strip() for name in m['jobs']}
    if any(s!='complete' for s in statuses.values()):print(json.dumps({'state':'not_complete','statuses':statuses}));return 3
    assert sha(data/'train_eval.jsonl')==m['train_sha256']==sha(v7/'train.jsonl')
    raw=[json.loads(l) for l in (data/'train_eval.jsonl').read_text().splitlines()]
    expected=[(r['_meta']['id'],qid) for r in raw for qid in r['questions']];assert len(raw)==1500 and len(expected)==2320
    known_weights=read(v7/'collected_evidence_index.json')['checkpoint_files_hashed_not_bundled'];files=set();reports={};checks={};loaded={}
    signature=lambda rs:[(r['id'],r['question'],r['keys'],r['label'],r['source']) for r in rs]
    for name,job in m['jobs'].items():
        folder=data/name;report=read(folder/'report.json');rows=read(folder/'rows.json');c=report['coverage'];checkpoint=Path(job['checkpoint'])
        assert Path(report['run']).resolve()==checkpoint.resolve() and report['data_sha256']==m['train_sha256']
        assert c['evaluated_records']==c['requested_records']==1500 and c['evaluated_questions']==c['requested_questions']==2320 and c['rejected_records']==c['truncated_records']==0
        assert [(r['id'],r['question']) for r in rows]==expected
        for filename in ['adapter_model.safetensors','head.pt','adapter_config.json']:
            p=checkpoint/filename;assert sha(p)==known_weights[str(p.relative_to(root))]
        loaded[name]=rows;reports[name]=report
        # All 140 probe contexts are exact materialized members of this corpus.
        model,stage=name.split('-');previous=root/'runs'/(model+'-20261030-targeted-v7')/('train-probe-before' if stage=='stage3' else 'train-probe-after')
        probe=read(previous/'rows.json');keys={(r['id'],r['question']):r for r in rows};deltas=[]
        for r in probe:
            full=keys[(r['id'],r['question'])];assert signature([r])==signature([full]);deltas.extend(abs(x-y) for x,y in zip(r['p'],full['p']))
        checks[name]={'contexts':1500,'questions':2320,'probe_questions':len(probe),'maximum_probe_probability_difference':max(deltas),'weights_match_completed_v7_archive':True}
        assert max(deltas)<1e-6,'Probe predictions changed; inspect before trusting acquisition comparison'
        files.update([previous/'rows.json',previous/'report.json'])
    for model in ['qwen3','qwen35']:assert signature(loaded[model+'-stage3'])==signature(loaded[model+'-v7'])
    for p in data.rglob('*'):
        if p.is_file() and p.suffix in ['.json','.jsonl','.py','.sh','.txt','.log'] and 'startup_evidence' not in p.parts and p.name not in ['collected_index.json','archive_result.json']:files.add(p)
    files.add(root/'collect_kev_training_fit_audit.py')
    result={'status':'verified_complete','checks':checks,'files':{str(p.relative_to(root)):sha(p) for p in sorted(files)},'created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Complete training-set acquisition diagnostic; no new training or independent generalization claim.'}
    ip=data/'collected_index.json';ip.write_text(json.dumps(result,indent=2)+'\n');files.add(ip)
    archive=data/'training-fit-verified-evidence.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(files):tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
    summary={'state':'collected','archive':str(archive),'sha256':sha(archive),'files':len(files),'checks':checks};(data/'archive_result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));return 0

if __name__=='__main__':raise SystemExit(main())
