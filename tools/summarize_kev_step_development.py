#!/usr/bin/env python3
"""Read step-development predictions and check unchanged primary branches."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from summarize_targeted_v4 import paired
from summarize_kev_training_fit_audit import counts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--remote',action='store_true');a=ap.parse_args();p=a.directory.resolve()
    launch=json.loads((p/'launch.json').read_text());path=p/'development_steps.jsonl';raw=[json.loads(l) for l in path.read_text().splitlines()]
    byid={r['_meta']['id']:r for r in raw};expected=[(r['_meta']['id'],q) for r in raw for q in r['questions']]
    h=hashlib.sha256(path.read_bytes()).hexdigest();result={'scope':'Same-generator development. Auxiliary-step accuracy is not official benchmark success. Primary-branch invariance compares the same weights with and without auxiliary questions.','data_sha256':h,'models':{}}
    for model,entry in launch['models'].items():
        run=Path(entry['run']) if a.remote else p/'evidence/runs'/Path(entry['run']).name
        loaded={};invariance={};primary_loaded={}
        for stage in ['before','after']:
            folder=run/('development-steps-'+stage)
            if not (folder/'report.json').exists():continue
            report=json.loads((folder/'report.json').read_text());rows=json.loads((folder/'rows.json').read_text());c=report['coverage']
            assert report['data_sha256']==h and c['evaluated_records']==c['requested_records']==334 and c['evaluated_questions']==c['requested_questions']==732 and c['rejected_records']==c['truncated_records']==0
            assert [(r['id'],r['question']) for r in rows]==expected
            loaded[stage]=rows
            primary=json.loads((run/('development-'+stage)/'rows.json').read_text());pi={(r['id'],r['question']):r for r in primary};assert len(pi)==488
            primary_loaded[stage]=primary
            for row in rows:
                if row['question']!='zz_rule_step':continue
                q=byid[row['id']]['questions'][row['question']]
                assert q['type']=='choice' and set(row['keys'])==set(q['criteria'])
                assert row['keys'][row['label']]==q['label']
            differences=[];agreements=[]
            for row in rows:
                if row['question']=='zz_rule_step':continue
                reference=pi[(row['id'],row['question'])]
                assert (reference['keys'],reference['label'],reference['source'])==(row['keys'],row['label'],row['source'])
                differences.extend(abs(x-y) for x,y in zip(row['p'],reference['p']))
                pick=lambda x:max(range(len(x['p'])),key=x['p'].__getitem__)
                agreements.append(pick(row)==pick(reference))
            assert len(agreements)==488
            invariance[stage]={'questions':488,'same_top_choice':sum(agreements),'max_absolute_probability_difference':max(differences)}
        if not loaded:result['models'][model]={'status':'pending'};continue
        assert 'before' in loaded
        pairs=paired(loaded['before'],loaded.get('after',loaded['before']));groups=defaultdict(list)
        for r in pairs:
            if r['question']=='zz_rule_step':
                meta=byid[r['id']]['_meta'];groups[meta['step_supervision']].append(r)
        summaries={k:counts(v) for k,v in sorted(groups.items())}
        if 'after' not in loaded:
            for s in summaries.values():
                for key in ['after_correct','after_pct','delta_pp','repaired','newly_wrong']:s[key]=None
        result['models'][model]={'status':'paired' if 'after' in loaded else 'before_only','primary_branch_invariance':invariance,'step_types':summaries}
        if 'after' in loaded:
            original_pairs=paired(primary_loaded['before'],primary_loaded['after'])
            by_context=defaultdict(list)
            for row in original_pairs:by_context[row['id']].append(row)
            transitions=defaultdict(list);joint=[]
            for step in pairs:
                if step['question']!='zz_rule_step':continue
                rid=step['id'];meta=byid[rid]['_meta'];primaries=by_context[rid]
                transition=('correct' if step['before_ok'] else 'wrong')+'->'+('correct' if step['after_ok'] else 'wrong')
                context={'id':rid,'family':meta['family'],'step_type':meta['step_supervision'],'step_transition':transition,
                         'primary_before_all_correct':all(x['before_ok'] for x in primaries),
                         'primary_after_all_correct':all(x['after_ok'] for x in primaries),
                         'primary_questions':len(primaries),'primary_repaired':sum(not x['before_ok'] and x['after_ok'] for x in primaries),
                         'primary_newly_wrong':sum(x['before_ok'] and not x['after_ok'] for x in primaries)}
                joint.append(context)
                for axis,value in [('family',meta['family']),('step_type',meta['step_supervision'])]:
                    transitions[(axis,value,transition)].extend(primaries)
            assert len(joint)==244
            result['models'][model]['step_primary_association']={
                'scope':'Descriptive association on same-generator development; final answers come from original inputs without auxiliary branches. This does not establish mediation or causality.',
                'strata':[{'axis':axis,'value':value,'step_transition':transition,**counts(rs)} for (axis,value,transition),rs in sorted(transitions.items())],
                'contexts':joint}
    (p/'step_development_diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({m:{k:v for k,v in r.items() if k not in ['step_types','step_primary_association']} for m,r in result['models'].items()}))

if __name__=='__main__':main()
