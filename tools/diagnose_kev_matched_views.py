#!/usr/bin/env python3
"""Describe a real prediction snapshot; never invent an unobserved after result."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def analyze(data, rows, pairs):
    expected=[(r['_meta']['id'],qid) for r in data for qid in r['questions']]
    assert [(r['id'],r['question']) for r in rows]==expected
    predictions={(r['id'],r['question']):r for r in rows}
    metadata={r['_meta']['id']:r['_meta'] for r in data}
    assert len(predictions)==len(rows)
    def pred(r):return max(range(len(r['p'])),key=r['p'].__getitem__)
    groups=defaultdict(Counter)
    for r in rows:
        m=metadata[r['id']]
        for group in [m['family'],m['family']+'/'+r['question'],m['family']+'/'+m.get('view_role','base')]:
            groups[group]['questions']+=1;groups[group]['correct']+=int(pred(r)==r['label'])
    pair_stats=defaultdict(Counter)
    for pair in pairs:
        family=pair['family'];a_id,b_id=pair['base_id'],pair['matched_id']
        question_ids=[q for rid,q in expected if rid==a_id]
        both_all=True
        for qid in question_ids:
            a,b=predictions[(a_id,qid)],predictions[(b_id,qid)]
            assert a['keys']==b['keys']
            gold_changed=a['label']!=b['label'];pred_changed=pred(a)!=pred(b)
            assert gold_changed==(qid in pair['changed_questions'])
            both=pred(a)==a['label'] and pred(b)==b['label'];both_all &= both
            for key in [family, family+'/'+qid, family+'/'+('gold_changes' if gold_changed else 'gold_unchanged')]:
                c=pair_stats[key];c['question_pairs']+=1;c['both_correct']+=int(both)
                c['both_wrong']+=int(pred(a)!=a['label'] and pred(b)!=b['label'])
                c['prediction_changed']+=int(pred_changed)
                c['expected_change_pattern_matched']+=int(gold_changed==pred_changed)
        pair_stats[family]['context_pairs']+=1
        pair_stats[family]['both_contexts_all_correct']+=int(both_all)
    policy=defaultdict(Counter)
    for r in data:
        if r['_meta']['family']!='policy':continue
        q=r['questions']['amount'];row=predictions[(r['_meta']['id'],'amount')]
        gold=q['criteria'][q['label']];chosen=q['criteria'][row['keys'][pred(row)]]
        positive=float(gold.replace('$','').replace(',',''))>0
        assert '$0.00' in q['criteria'].values()
        for key in ['positive' if positive else 'zero',('positive' if positive else 'zero')+'/'+r['_meta'].get('view_role','base')]:
            c=policy[key];c['records']+=1;c['correct_amount']+=int(chosen==gold);c['chose_zero']+=int(chosen=='$0.00')
    return {'accuracy_groups':dict(groups),'matched_pairs':dict(pair_stats),'policy_zero_choice':dict(policy)}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--evidence',type=Path);ap.add_argument('--phase',choices=['before','after'],default='before');a=ap.parse_args();p=a.directory;e=a.evidence or p/'evidence'
    mapping=json.loads((p/'pair_mapping.json').read_text());out={'phase':a.phase,'models':{},'scope':'Observed predictions only. Training scores are in-sample; development uses shared generators. Prediction changes alone do not imply correctness. Extra paired views are not independent base cases.'}
    for model in ['qwen3','qwen35']:
        run=e/'runs'/(model+'-20261030-targeted-v9-matched');out['models'][model]={}
        for kind,split in [('development','development'),('full-train','train')]:
            folder=run/(kind+'-'+a.phase)
            if not (folder/'report.json').exists():
                out['models'][model][split]={'status':'not_available'};continue
            f=p/(split+'.jsonl');data=[json.loads(l) for l in f.read_text().splitlines()];report=json.loads((folder/'report.json').read_text());rows=json.loads((folder/'rows.json').read_text());c=report['coverage']
            assert report['data_sha256']==hashlib.sha256(f.read_bytes()).hexdigest()
            assert c['requested_records']==c['evaluated_records']==len(data)
            assert c['requested_questions']==c['evaluated_questions']==len(rows) and c['rejected_records']==c['truncated_records']==0
            original='qwen3-06b-20261026' if model=='qwen3' else 'replica-20261026'
            expected=(original+'/stage3') if a.phase=='before' else (model+'-20261030-targeted-v9-matched/stage4')
            assert report['run'].endswith('/runs/'+expected)
            out['models'][model][split]={'status':'complete','data_sha256':report['data_sha256'],**analyze(data,rows,mapping[split])}
    (p/('matched_views_'+a.phase+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({m:{s:r.get('matched_pairs',r) for s,r in v.items()} for m,v in out['models'].items()},ensure_ascii=False))


if __name__=='__main__':main()
