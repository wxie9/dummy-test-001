#!/usr/bin/env python3
"""Collect a completed two-model control, validating coverage and lineage first."""
import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

VARIANTS={
    'v9-matched':('targeted_v9_matched_20261030',1,'2932da30f01f37e6443f911399fa6195e99ca8605a5e92c85dcec7ba1896352d'),
    'v8-steps':('targeted_v8_steps_20261030',1,'3118273464feb4ef80e9739a840a841a2c5accf162b87cc0d3467ee24855ff98'),
    'v7-lr5':('targeted_v7_lr5_20261030',1,'51bd77f674d62bf9600c91d3dec2b52297e48c686198e2569dacb4f75dbf2845'),
    'v7':('targeted_v7_20261030',1,'51bd77f674d62bf9600c91d3dec2b52297e48c686198e2569dacb4f75dbf2845'),
    'v6-factmix':('targeted_v6_factmix_candidate_20261030',1,'2f50313e50370372cf232a998280a4f5bbc26f98dd59ddef2ee8872f870fe243'),
    'v6-3ep':('targeted_v6_3ep_20261030',3,'58572b2118b10d9505d5bdb027585fab75f4ad7e52a1c5d8d155979459fecea8'),
    'v6':('targeted_v6_20261030',1,'58572b2118b10d9505d5bdb027585fab75f4ad7e52a1c5d8d155979459fecea8'),
    'v5-3ep':('targeted_v5_3ep_20261030',3,'50d76359f88eafc75392218a70538adc966640f567de06c0852a492cb80bc463'),
    'v5-guard':('targeted_v5_none_guard_candidate_20261030',1,'7d2493876883c394f36e6c26389a102d9dab99b187915f0f6eaf283106ac7e52'),
}

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def check_report(folder,checkpoint):
    report=read(folder/'report.json');rows=read(folder/'rows.json');c=report['coverage']
    assert c['rejected_records']==c['truncated_records']==0
    assert c['evaluated_questions']==c['requested_questions']==len(rows)
    assert Path(report['run']).resolve()==checkpoint.resolve()
    return report,rows


def aligned(a,b):
    # Retain duplicate-id occurrences in their frozen order.
    signature=lambda rs:[(r['id'],r['question'],r['keys'],r['label'],r['source']) for r in rs]
    assert signature(a)==signature(b),'Before/after evaluation alignment mismatch'


def check_raw_coverage(path, report, rows):
    records=[json.loads(line) for line in path.read_text().splitlines()]
    expected=[(r['_meta']['id'], qid) for r in records for qid in r['questions']]
    assert [(r['id'],r['question']) for r in rows]==expected
    coverage=report['coverage']
    assert coverage['evaluated_records']==coverage['requested_records']==len(records)
    assert coverage['evaluated_questions']==len(expected)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--version',choices=VARIANTS,required=True);a=ap.parse_args()
    root=a.root.resolve();folder,epochs,data_hash=VARIANTS[a.version];data=root/folder
    runnames=[m+'-20261030-targeted-'+a.version for m in ['qwen3','qwen35']]
    status={n:(root/'runs'/n/'status.txt').read_text().strip() for n in runnames}
    if any(s!='complete' for s in status.values()):
        print(json.dumps({'state':'not_complete','runs':status}));return 3
    assert sha(data/'train.jsonl')==data_hash
    files=set();checkpoint_hashes={};checks={}
    for name,original in zip(runnames,['qwen3-06b-20261026','replica-20261026']):
        run=root/'runs'/name;old=root/'runs'/original;checkpoint=run/'stage4'
        config=read(checkpoint/'training_config.json');metrics=read(checkpoint/'training_metrics.json');args=config['args']
        assert args['epochs']==epochs and args['seed']==101 and args['replay']==6000
        expected_settings={'lr':5e-5 if a.version=='v7-lr5' else 1e-5,'lora':16,'accum':2,'batch':4,'head_lr':0.0,
            'weight_decay':0.01,'perm_kl':0.0,'perm_frac':0.3,'ord_w':0.0,
            'p_none':0.1,'p_none_distract':0.12,'p_distract':0.15,'p_none_pair':0.25,
            'synthetic_repeat':1,'public_frac':1.0,'anchor_w':0.0,'label_smoothing':0.0,
            'brier_w':0.0,'focal_gamma':0.0,'dtype':'bf16','checkpointing':1,'max_state':7552}
        assert all(args[k]==v for k,v in expected_settings.items()),'Training settings differ from frozen plan'
        assert Path(args['data']).resolve()==(data/'train.jsonl').resolve()
        assert Path(args['init_from']).resolve()==(old/'stage3').resolve()
        init=config['init_source']
        assert Path(init['resolved']).resolve()==(old/'stage3').resolve()
        assert init['adapter_sha256']==sha(old/'stage3/adapter_model.safetensors')
        assert init['head_sha256']==sha(old/'stage3/head.pt')
        expected_records,expected_steps=(8520,1065) if a.version=='v9-matched' else (7500,938)
        assert metrics['requested_records']==epochs*expected_records and metrics['optimizer_steps']==epochs*expected_steps
        assert metrics['rejected_records']==metrics['truncated_records']==0
        for kind,file in [('development','development.jsonl'),('train-probe','train_probe.jsonl')]:
            br,b=check_report(run/(kind+'-before'),old/'stage3')
            ar,c=check_report(run/(kind+'-after'),checkpoint)
            assert br['data_sha256']==ar['data_sha256']==sha(data/file)
            aligned(b,c)
            check_raw_coverage(data/file,br,b)
            check_raw_coverage(data/file,ar,c)
            reference_version='v7' if a.version in ['v7-lr5','v8-steps','v9-matched'] else 'v6' if a.version in ['v6-3ep','v6-factmix','v7'] else 'v5'
            reference=read(root/'runs'/(name.split('-20261030-')[0]+'-20261030-targeted-'+reference_version)/(kind+'-before')/'rows.json')
            if a.version=='v6-factmix':
                aligned(reference,b)
                current_raw=[json.loads(line) for line in (data/file).read_text().splitlines()]
                original_raw=[json.loads(line) for line in (root/'targeted_v6_20261030'/file).read_text().splitlines()]
                assert [r['_meta']['id'] for r in current_raw]==[r['_meta']['id'] for r in original_raw]
                unchanged=set()
                for x,y in zip(original_raw,current_raw):
                    assert x['questions']==y['questions']
                    if x['state']==y['state']:unchanged.add(x['_meta']['id'])
                assert len(unchanged)==(336 if kind=='development' else 131)
                for x,y in zip(reference,b):
                    if x['id'] in unchanged:assert x['p']==y['p'],'Unchanged original baseline predictions changed'
            elif a.version in ['v6','v7','v9-matched']:
                # New development/probe cases cannot be compared to v5 as an
                # identical dataset. Only the unchanged retained dev cases can.
                if kind=='development':
                    by_key={(r['id'],r['question']):r for r in reference}
                    shared=[r for r in b if (r['id'],r['question']) in by_key]
                    assert len(shared)==90
                    for r in shared:
                        previous=by_key[(r['id'],r['question'])]
                        aligned([previous],[r])
                        assert previous['p']==r['p'],'Retained original baseline predictions changed'
            else:
                aligned(reference,b)
                assert all(x['p']==y['p'] for x,y in zip(reference,b)), 'Original baseline predictions changed'
        if a.version=='v9-matched':
            assert read(run/'baseline_gate.json')['passed'] is True
            br,before=check_report(run/'full-train-before',old/'stage3')
            ar,after=check_report(run/'full-train-after',checkpoint)
            assert br['data_sha256']==ar['data_sha256']==data_hash
            aligned(before,after)
            check_raw_coverage(data/'train.jsonl',br,before)
            check_raw_coverage(data/'train.jsonl',ar,after)
            base_rows=[json.loads(l) for l in (data/'train_base.jsonl').read_text().splitlines()]
            all_rows=[json.loads(l) for l in (data/'train.jsonl').read_text().splitlines()]
            assert len(base_rows)==1500 and len(all_rows)==2520
            lookup={r['_meta']['id']:r for r in all_rows}
            assert all(lookup[r['_meta']['id']]==r for r in base_rows)
            pairs=read(data/'pair_mapping.json')['train'];assert len(pairs)==1020
            for pair in pairs:
                x,y=lookup[pair['base_id']],lookup[pair['matched_id']]
                for qid,q in x['questions'].items():
                    assert {k:v for k,v in q.items() if k not in ['label','target']}=={k:v for k,v in y['questions'][qid].items() if k not in ['label','target']}
            retained={'tool_routing','temporal','injection'}
            select=lambda path:{r['_meta']['id']:l for l in path.read_text().splitlines() if (r:=json.loads(l))['_meta']['family'] in retained}
            assert select(data/'train_base.jsonl')==select(root/'targeted_v7_20261030/train.jsonl')
        if a.version in ['v7-lr5','v8-steps']:
            fit=root/'v7_training_fit_audit_20261030';model=name.split('-20261030-')[0]
            ar,after=check_report(run/'full-train-after',checkpoint)
            full_data=data/('train_original.jsonl' if a.version=='v8-steps' else 'train.jsonl')
            check_raw_coverage(full_data,ar,after)
            assert ar['data_sha256']==sha(full_data)
            for stage,cp in [('stage3',old/'stage3'),('v7',root/'runs'/(model+'-20261030-targeted-v7')/'stage4')]:
                folder=fit/(model+'-'+stage);br,before=check_report(folder,cp)
                assert br['data_sha256']==ar['data_sha256'];aligned(before,after)
                check_raw_coverage(full_data,br,before)
                files.update([folder/'report.json',folder/'rows.json'])
        if a.version=='v8-steps':
            assert read(run/'baseline_gate.json')['passed'] is True
            step_data=data/'development_steps.jsonl'
            br,before=check_report(run/'development-steps-before',old/'stage3')
            ar,after=check_report(run/'development-steps-after',checkpoint)
            assert br['data_sha256']==ar['data_sha256']==sha(step_data)
            aligned(before,after)
            check_raw_coverage(step_data,br,before);check_raw_coverage(step_data,ar,after)
            original_records=[json.loads(l) for l in (data/'train_original.jsonl').read_text().splitlines()]
            new_records=[json.loads(l) for l in (data/'train.jsonl').read_text().splitlines()]
            assert len(original_records)==len(new_records)==1500
            added=0
            for x,y in zip(original_records,new_records):
                assert x['_meta']['id']==y['_meta']['id'] and x['state']==y['state']
                assert all(y['questions'][qid]==q for qid,q in x['questions'].items())
                extra=set(y['questions'])-set(x['questions'])
                if x['_meta']['family'] in ['tool_routing','temporal','injection']:assert not extra and x==y
                else:assert extra=={'zz_rule_step'};added+=1
            assert added==1200
        for suite in ['hard-v1','devtools-v1']:
            baseline=old/'benchmarks'/(suite+'-test')
            br,b=check_report(baseline,old/'stage3')
            ar,c=check_report(run/('eval-'+suite),checkpoint)
            assert br['suite_sha256']==ar['suite_sha256']
            assert ar.get('date_facts') in [False,None] and ar.get('rotations') in [0,1,None]
            aligned(b,c)
            check_raw_coverage(root/'evals'/suite/'test.jsonl',ar,c)
            files.update([baseline/'report.json',baseline/'rows.json'])
        for p in run.rglob('*'):
            if p.is_file() and (p.suffix in ['.json','.jsonl','.log'] or p.name=='status.txt') and p.name!='tokenizer.json':files.add(p)
        for cp in [old/'stage3',checkpoint]:
            for filename in ['head.pt','adapter_model.safetensors','adapter_config.json']:
                path=cp/filename;assert path.is_file();checkpoint_hashes[str(path.relative_to(root))]=sha(path)
        checks[name]={'epochs':epochs,'optimizer_steps':metrics['optimizer_steps'],'all_reports_complete_and_aligned':True}
    for p in data.iterdir():
        if p.is_file() and p.suffix in ['.json','.jsonl','.log','.py','.sh'] and p.name not in ['collected_evidence_index.json']:files.add(p)
    for name in ['train.py','data.py','api.py','model.py','suite.py']:files.add(root/'stages/stage3/kev'/name)
    files.add(root/'collect_kev_control_evidence.py')
    for suite in ['hard-v1','devtools-v1']:files.add(root/'evals'/suite/'test.jsonl')
    index={'version':a.version,'created_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,
           'files':{str(p.relative_to(root)):sha(p) for p in sorted(files)},
           'checkpoint_files_hashed_not_bundled':checkpoint_hashes,'goal_achieved':False}
    ip=data/'collected_evidence_index.json';ip.write_text(json.dumps(index,indent=2)+'\n');files.add(ip)
    archive=data/(a.version+'-verified-evidence.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(files):tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
    result={'state':'collected','archive':str(archive),'sha256':sha(archive),'files':len(files),'checks':checks}
    (data/'archive_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
