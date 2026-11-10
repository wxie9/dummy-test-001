#!/usr/bin/env python3
"""Measure payment-option preference and paired-answer inconsistency."""
import json
import hashlib
import argparse
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'v7_representation_probe_20261030'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate-dir',type=Path,help='Completed control directory containing launch.json and evidence/runs.')
    ap.add_argument('--output-dir',type=Path,help='Defaults to candidate directory when supplied, otherwise original probe directory.')
    args=ap.parse_args()
    out=(args.output_dir or args.candidate_dir or OUT).resolve()
    stages=['stage3','v7','lr5']
    candidate_runs={}
    if args.candidate_dir:
        directory=args.candidate_dir.resolve()
        launch=json.loads((directory/'launch.json').read_text())
        candidate_runs={model:directory/'evidence/runs'/Path(entry['run']).name for model,entry in launch['models'].items()}
        assert set(candidate_runs)=={'qwen3','qwen35'}
        stages.append('candidate')
        # Validate all required files before writing either result.
        for run in candidate_runs.values():
            for phase in ['full-train-after','eval-hard-v1']:
                assert (run/phase/'rows.json').is_file(),str(run/phase/'rows.json')
    data=BASE/'targeted_v7_20261030/train.jsonl'
    raw={r['_meta']['id']:r for r in map(json.loads,data.read_text().splitlines()) if r['_meta']['family']=='policy'}
    result={'scope':'Descriptive audit of original training inputs, not intervention or generalization evidence. Predicted pay reason plus predicted zero amount is measured only where the gold payment is strictly positive.','jobs':{},'source_hashes':{str(data):hashlib.sha256(data.read_bytes()).hexdigest()}}
    for model in ['qwen3','qwen35']:
        for stage in stages:
            if stage in ['stage3','v7']:
                p=BASE/'v7_training_fit_audit_20261030/evidence/v7_training_fit_audit_20261030'/(model+'-'+stage)/'rows.json'
            elif stage=='candidate':p=candidate_runs[model]/'full-train-after/rows.json'
            else:p=BASE/'targeted_v7_lr5_20261030/evidence/runs'/(model+'-20261030-targeted-v7-lr5')/'full-train-after/rows.json'
            result['source_hashes'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
            byid=defaultdict(dict)
            for x in json.loads(p.read_text()):
                if x['id'] not in raw:continue
                q=raw[x['id']]['questions'][x['question']]
                assert x['question'] not in byid[x['id']]
                assert set(x['keys'])==set(q['criteria'])
                assert x['keys'][x['label']]==q['label']
                key=x['keys'][max(range(len(x['p'])),key=x['p'].__getitem__)]
                byid[x['id']][x['question']]=q['criteria'][key]
            counts=Counter();groups=defaultdict(Counter)
            for rid,r in raw.items():
                answers=byid[rid];q=r['questions']['amount'];gold=q['criteria'][q['label']]
                assert set(answers)=={'amount','reason'}
                positive=float(gold.replace('$','').replace(',',''))>0
                zero_offered='$0.00' in q['criteria'].values();pred_zero=answers['amount']=='$0.00'
                predicted_pay=answers['reason'].startswith('Pay ')
                stratum=('positive' if positive else 'zero')+'/zero_offered='+str(zero_offered)
                g=groups[stratum];g['contexts']+=1;g['correct_amount']+=answers['amount']==gold
                g['predicted_zero']+=pred_zero;g['predicted_pay_reason']+=predicted_pay
                g['pay_reason_and_zero_amount']+=predicted_pay and pred_zero
                if positive:
                    counts['positive_contexts']+=1;counts['positive_predicted_pay_reason']+=predicted_pay
                    counts['positive_pay_reason_but_zero_amount']+=predicted_pay and pred_zero
            result['jobs'][model+'-'+stage]={'summary':dict(counts),'strata':{k:dict(v) for k,v in groups.items()}}
    for name,x in result['jobs'].items():print(name,x)
    test_path=BASE/'targeted_v7_lr5_20261030/evidence/evals/hard-v1/test.jsonl'
    test={r['_meta']['id']:r for r in map(json.loads,test_path.read_text().splitlines()) if r['_meta']['source']=='hard_long_policy'}
    test_result={'scope':'Already-inspected official diagnostic cases. Descriptive answer inconsistency; not independent confirmation or a causal test.','jobs':{},'source_hashes':{str(test_path):hashlib.sha256(test_path.read_bytes()).hexdigest()}}
    for model,original in [('qwen3','qwen3-06b-20261026'),('qwen35','replica-20261026')]:
        for stage in stages:
            if stage=='stage3':path=BASE/'targeted_v7_lr5_20261030/evidence/runs'/original/'benchmarks/hard-v1-test/rows.json'
            elif stage=='candidate':path=candidate_runs[model]/'eval-hard-v1/rows.json'
            else:
                version='v7' if stage=='v7' else 'v7-lr5';folder='targeted_v7_20261030' if stage=='v7' else 'targeted_v7_lr5_20261030'
                path=BASE/folder/'evidence/runs'/(model+'-20261030-targeted-'+version)/'eval-hard-v1/rows.json'
            test_result['source_hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            observed=defaultdict(dict)
            for x in json.loads(path.read_text()):
                if x['id'] in test:
                    q=test[x['id']]['questions'][x['question']]
                    assert x['question'] not in observed[x['id']]
                    assert set(x['keys'])==set(q['criteria'])
                    assert x['keys'][x['label']]==q['label']
                    key=x['keys'][max(range(len(x['p'])),key=x['p'].__getitem__)]
                    observed[x['id']][x['question']]=test[x['id']]['questions'][x['question']]['criteria'][key]
            groups=defaultdict(Counter)
            money=lambda value:float(value.replace('$','').replace(',',''))
            for rid,r in test.items():
                q=r['questions']['amount'];gold=money(q['criteria'][q['label']]);answers=observed[rid]
                assert set(answers)=={'amount','outcome'}
                offered=any(money(v)==0 for v in q['criteria'].values());zero=money(answers['amount'])==0
                key=('positive' if gold>0 else 'zero')+'/zero_offered='+str(offered);g=groups[key]
                g['contexts']+=1;g['correct_amount']+=money(answers['amount'])==gold;g['predicted_zero']+=zero
                g['pay_reason_and_zero_amount']+=answers['outcome'].startswith('Pay ') and zero
            test_result['jobs'][model+'-'+stage]={k:dict(v) for k,v in groups.items()}
    if candidate_runs:
        for record in [result,test_result]:
            record['candidate_directory']=str(args.candidate_dir.resolve())
            record['candidate_runs']={m:str(p) for m,p in candidate_runs.items()}
    out.mkdir(parents=True,exist_ok=True)
    (out/'zero_preference_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'real_policy_zero_preference_audit.json').write_text(json.dumps(test_result,indent=2)+'\n')
    for name,v in test_result['jobs'].items():print('REAL',name,v)

if __name__=='__main__':main()
