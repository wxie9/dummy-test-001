#!/usr/bin/env python3
"""Candidate replacement component; no training launch and no v5 mutation.

All three answer wordings appear uniformly; no item-level choice of the best
wording from evaluation. Two auxiliary questions teach evidence sufficiency.
"""
import copy
import hashlib
import json
from pathlib import Path
from build_kev_option_surface_probe import ACTION, CANONICAL, V5
from check_targeted_v4_rules import missing, materialize

OUT=V5.with_name('insufficient_multiview_candidates_20261030')
VERSION='insufficient-multiview-candidate-20261030'

def verify(r):
    decisions=missing(r)  # Recomputed from visible dates, amounts and bounds.
    role='unknown' if len(decisions)>1 else 'yes' if True in decisions else 'no'
    for name in ['decision','decision_action','decision_concise']:
        q=r['questions'][name]
        assert r['_meta']['question_option_roles'][name][q['label']]==role
    assert r['questions']['evidence_supports_yes']['label']==(decisions=={True})
    assert r['questions']['evidence_supports_no']['label']==(decisions=={False})
    materialize(r)

def main():
    OUT.mkdir(exist_ok=True)
    manifest={'status':'candidate_only_not_in_training','purpose':'Candidate replacement for the 280-context insufficient-information component; not a complete 1500-context corpus and not additional unique cases.',
        'source':'Frozen v5 cases, unchanged state and ground-truth decision; all views used uniformly, never selected per item according to model performance.',
        'scope':'Development shares generators and was already used for diagnosis. No independent-generalization claim.', 'files':{}}
    for split in ['train','development']:
        originals=[json.loads(l) for l in (V5/(split+'.jsonl')).read_text().splitlines()]
        originals=[r for r in originals if r['_meta']['family']=='insufficient'];rows=[];rejected_mutations=0
        for original in originals:
            r=copy.deepcopy(original);q=r['questions']['decision'];roles={k:CANONICAL[v] for k,v in q['criteria'].items()}
            correct=roles[q['label']];scenario=r['_meta']['facts']['scenario'];action=dict(zip(['yes','no'],ACTION[scenario]))
            action['unknown']='The supplied facts do not settle this decision.'
            concise={'yes':'Yes','no':'No','unknown':'Cannot be determined'}
            maps={'decision':roles}
            for name,descs in [('decision_action',action),('decision_concise',concise)]:
                view=copy.deepcopy(q);view['criteria']={k:descs[role] for k,role in roles.items()};r['questions'][name]=view;maps[name]=dict(roles)
            prompt=q['instructions'].removesuffix(' Use only the supplied facts.')
            r['questions']['evidence_supports_yes']={'type':'noul','instructions':f'For the decision "{prompt}", do the stated facts and rule guarantee a yes answer? A merely possible yes is not enough.','label':correct=='yes','src':VERSION}
            r['questions']['evidence_supports_no']={'type':'noul','instructions':f'For the decision "{prompt}", do the stated facts and rule guarantee a no answer? A merely possible no is not enough.','label':correct=='no','src':VERSION}
            m=r['_meta'];m['derived_from']=m['id'];m['id']=VERSION+'/'+m['id'];m['source']=VERSION;m['question_option_roles']=maps
            for spec in r['questions'].values():spec['src']=VERSION
            assert r['state']==original['state'];verify(r)
            # Test all five labels, including the new evidence-entailment labels.
            for name,spec in r['questions'].items():
                bad=copy.deepcopy(r);bq=bad['questions'][name]
                bq['label']=not bq['label'] if bq['type']=='noul' else next(k for k in bq['criteria'] if k!=bq['label'])
                try:verify(bad)
                except AssertionError:rejected_mutations+=1
                else:raise AssertionError(('bad label accepted',m['id'],name))
            rows.append(r)
        p=OUT/(split+'.candidate.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'all_wrong_label_mutations_rejected':rejected_mutations,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
