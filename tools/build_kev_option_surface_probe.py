#!/usr/bin/env python3
"""Paired option-wording diagnostic on v5 development, never training data."""
import copy
import hashlib
import json
from pathlib import Path
from build_targeted_v5 import OUT as V5, ROOT
from check_targeted_v4_rules import materialize

OUT=V5.with_name('option_surface_probe_20261030')
CANONICAL={'The requirement is satisfied':'yes','The requirement is not satisfied':'no','Cannot determine from the information given':'unknown'}
ACTION={
    'return':('Authorize this return.','Do not authorize this return.'),
    'approval':('The payment authorization is adequate.','The payment authorization is inadequate.'),
    'tenure':('Grant the stated employment benefit.','Do not grant the stated employment benefit.'),
    'shipping':('Apply zero shipping charges.','Apply standard shipping charges.'),
    'overtime':('Treat some of the week as overtime.','No overtime is due for this week.'),
    'warranty':('Honor this warranty claim.','Decline coverage for this warranty claim.'),
    'price_match':('Honor the requested price match.','Decline the requested price match.'),
}

def main():
    OUT.mkdir(exist_ok=True)
    originals=[json.loads(l) for l in (V5/'development.jsonl').read_text().splitlines()]
    originals=[r for r in originals if r['_meta']['family']=='insufficient'];assert len(originals)==70
    rows=[]
    for original in originals:
        q0=original['questions']['decision'];role_map={k:CANONICAL[v] for k,v in q0['criteria'].items()}
        correct=role_map[q0['label']];scenario=original['_meta']['facts']['scenario']
        action=dict(zip(['yes','no'],ACTION[scenario]));action['unknown']='The supplied facts do not settle this decision.'
        for variant in ['original','semantic_keys','action_descriptions','concise_descriptions']:
            r=copy.deepcopy(original);q=r['questions']['decision'];keys={k:k for k in q0['criteria']}
            if variant=='semantic_keys':keys={k:{'yes':'condition_met','no':'condition_not_met','unknown':'information_insufficient'}[role_map[k]] for k in q0['criteria']}
            values=q0['criteria'] if variant in ['original','semantic_keys'] else {k:action[role_map[k]] for k in q0['criteria']} if variant=='action_descriptions' else {k:{'yes':'Yes','no':'No','unknown':'Cannot be determined'}[role_map[k]] for k in q0['criteria']}
            q['criteria']={keys[k]:values[k] for k in q0['criteria']};q['label']=keys[q0['label']]
            m=r['_meta'];m.update(id='option-surface/'+variant+'/'+original['_meta']['id'],source='option_surface_probe',
                group_id=original['_meta']['id'],surface_variant=variant,canonical_option_roles={keys[k]:v for k,v in role_map.items()},correct_role=correct,original_id=original['_meta']['id'])
            assert r['state']==original['state'] and q['instructions']==q0['instructions']
            assert list(m['canonical_option_roles'].values())==list(role_map.values())
            assert m['canonical_option_roles'][q['label']]==correct
            materialize(r);rows.append(r)
    # Do not sort keys: semantic-key sorting would also change option order,
    # confounding the key-only intervention with a position intervention.
    p=OUT/'probe.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    original_roles={r['_meta']['id']:[CANONICAL[v] for v in r['questions']['decision']['criteria'].values()] for r in originals}
    for r in map(json.loads,p.read_text().splitlines()):
        m=r['_meta'];assert [m['canonical_option_roles'][k] for k in r['questions']['decision']['criteria']]==original_roles[m['original_id']]
    manifest={'status':'prepared_not_evaluated','contexts':280,'underlying_cases':70,'questions':280,'variants':['original','semantic_keys','action_descriptions','concise_descriptions'],
        'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'Within-case option-language intervention on already-used development cases; not a new heldout test and never added to training.',
        'controls':'State, question, option order and semantic gold are unchanged. Key-only variant changes only keys; wording variants change only descriptions.',
        'limitations':'Authored paraphrases checked manually and by canonical mapping; no external semantic reviewer. Sensitivity does not alone establish the cause of real-benchmark regressions.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    evaluator=(V5/'evaluate_development.py').read_text().replace('same-generator development; not independent heldout','within-case option wording diagnostic; not heldout')
    (OUT/'evaluate.py').write_text(evaluator)
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
