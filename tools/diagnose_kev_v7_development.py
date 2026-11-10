#!/usr/bin/env python3
"""Describe fixed v7 development predictions by authored mechanism; no inference."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

def axes(record,qid):
    m=record['_meta'];f=m['family'];facts=m.get('facts',{});out=[('family',f),('family_question',f+'/'+qid)]
    if f not in ['probability','multihop','insufficient','policy']:return out
    out.append(('subtype',f+'/'+m['subtype']+'/'+qid))
    keys={'probability':['target_row_position','target_status_position','layout'],
          'multihop':['chain_hops','desired_contact_position','shape'],
          'insufficient':['scenario','variant'],
          'policy':['domain','cover_count','named_item_claim','deduct_before_cap','threshold_trigger','threshold_exception','flag_trigger','flag_exception']}[f]
    for k in keys:
        if k in facts:out.append((f+'/'+k,str(facts[k])+'/'+qid))
    for k in ['rate_style','presentation']:
        if k in m:out.append((f+'/'+k,str(m[k])+'/'+qid))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('data',type=Path);a=ap.parse_args();data=a.data.resolve()
    raw=[json.loads(l) for l in (data/'development.jsonl').read_text().splitlines()];byid={r['_meta']['id']:r for r in raw}
    expected=[(r['_meta']['id'],qid) for r in raw for qid in r['questions']];sha=hashlib.sha256((data/'development.jsonl').read_bytes()).hexdigest()
    output={'scope':'Fixed same-generator development, not independent generalization. Subgroups overlap and can be small; no significance claim. Missing after means training/post-evaluation unfinished, not zero accuracy.','data_sha256':sha,'models':{}}
    launch=json.loads((data/'launch.json').read_text())
    for model,e in launch['models'].items():
        run=Path(e['run']);loaded={}
        for stage in ['before','after']:
            folder=run/('development-'+stage)
            if not (folder/'report.json').exists():continue
            report=json.loads((folder/'report.json').read_text());rows=json.loads((folder/'rows.json').read_text());c=report['coverage']
            assert report['data_sha256']==sha and c['rejected_records']==c['truncated_records']==0
            assert c['evaluated_records']==c['requested_records']==len(raw)
            assert c['evaluated_questions']==c['requested_questions']==len(expected)
            assert [(r['id'],r['question']) for r in rows]==expected
            loaded[stage]=rows
        assert 'before' in loaded
        if 'after' in loaded:
            assert [(r['keys'],r['label'],r['source']) for r in loaded['before']]==[(r['keys'],r['label'],r['source']) for r in loaded['after']]
        groups=defaultdict(list)
        for i,row in enumerate(loaded['before']):
            old=max(range(len(row['p'])),key=row['p'].__getitem__)==row['label'];new=None
            if 'after' in loaded:
                r=loaded['after'][i];new=max(range(len(r['p'])),key=r['p'].__getitem__)==r['label']
            for axis,value in axes(byid[row['id']],row['question']):groups[(axis,value)].append((row['id'],old,new))
        results=[]
        for (axis,value),items in sorted(groups.items()):
            r={'axis':axis,'value':value,'questions':len(items),'contexts':len({i[0] for i in items}),'before_correct':sum(i[1] for i in items),'after_correct':None}
            if 'after' in loaded:r.update(after_correct=sum(i[2] for i in items),repaired=sum(not i[1] and i[2] for i in items),newly_wrong=sum(i[1] and not i[2] for i in items))
            results.append(r)
        output['models'][model]={'stage':'paired' if 'after' in loaded else 'baseline_only','subgroups':results}
    (data/'development_coverage_diagnostics.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({model:[g for g in m['subgroups'] if g['axis']=='family'] for model,m in output['models'].items()}))

if __name__=='__main__':main()
