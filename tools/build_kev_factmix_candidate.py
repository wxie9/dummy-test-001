#!/usr/bin/env python3
"""Single-factor 1500-context candidate: rewrite 140 insufficient states.

Preserve row order, IDs, questions, labels, augmentation seeds and other six
families. Within scenario/pair-kind/complete-answer strata, rewrite half the
pairs. Both siblings use the same style. No training is launched.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from build_kev_fact_surface_probe import prose, unprose, tree
from build_kev_insufficient_multiview_candidates import verify
from build_targeted_v5 import digest
from check_targeted_v4_rules import materialize, gold

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/kev_training_eval_20261026/targeted_v6_20261030'
OUT=SOURCE.with_name('targeted_v6_factmix_candidate_20261030')
VERSION='v6-factmix-candidate-20261030'

def rewrite(s):
    s=prose(s)
    s=re.sub(r'Amount: \$(\d+)\.',lambda m:f'The payment amount is ${int(m[1]):.2f}.',s)
    s=re.sub(r'Actual approver: (\w+)\.',lambda m:f'The person who actually approved is {m[1]}.',s)
    for old,new in [('Company hire date','The company employment began on'),('Claim received','The warranty claim arrived on')]:
        s=re.sub(re.escape(old)+r': (\d{4}-\d{2}-\d{2})\.',lambda m:new+' '+datetime.strptime(m[1],'%Y-%m-%d').strftime('%B %d, %Y')+'.',s)
    s=re.sub(r'(\w+) transferred to the Support team on (\d{4}-\d{2}-\d{2})\.',
        lambda m:m[1]+' moved to the Support team on '+datetime.strptime(m[2],'%Y-%m-%d').strftime('%B %d, %Y')+'.',s)
    s=re.sub(r'Technician confirmed cause: (manufacturing defect|accidental damage)\.',lambda m:f'The technician identified {m[1]} as the cause.',s)
    s=re.sub(r'Our price: \$(\d+)\.',lambda m:f'We charge ${int(m[1]):.2f} for the item.',s)
    s=re.sub(r'Competitor price: \$(\d+)\.',lambda m:f'The competitor charges ${int(m[1]):.2f} for the item.',s)
    s=re.sub(r'Competitor inventory: (in stock|out of stock)\.',lambda m:f'At the competitor, the item is {m[1]}.',s)
    return s

def restore(s):
    s=unprose(s)
    s=re.sub(r'The payment amount is \$(\d+)\.00\.',lambda m:f'Amount: ${int(m[1])}.',s)
    s=re.sub(r'The person who actually approved is (\w+)\.',lambda m:f'Actual approver: {m[1]}.',s)
    for old,new in [('Company hire date','The company employment began on'),('Claim received','The warranty claim arrived on')]:
        s=re.sub(re.escape(new)+r' ([A-Za-z]+ \d{2}, \d{4})\.',lambda m:old+': '+datetime.strptime(m[1],'%B %d, %Y').strftime('%Y-%m-%d')+'.',s)
    s=re.sub(r'(\w+) moved to the Support team on ([A-Za-z]+ \d{2}, \d{4})\.',
        lambda m:m[1]+' transferred to the Support team on '+datetime.strptime(m[2],'%B %d, %Y').strftime('%Y-%m-%d')+'.',s)
    s=re.sub(r'The technician identified (manufacturing defect|accidental damage) as the cause\.',lambda m:f'Technician confirmed cause: {m[1]}.',s)
    s=re.sub(r'We charge \$(\d+)\.00 for the item\.',lambda m:f'Our price: ${int(m[1])}.',s)
    s=re.sub(r'The competitor charges \$(\d+)\.00 for the item\.',lambda m:f'Competitor price: ${int(m[1])}.',s)
    s=re.sub(r'At the competitor, the item is (in stock|out of stock)\.',lambda m:f'Competitor inventory: {m[1]}.',s)
    return s

def main():
    OUT.mkdir(exist_ok=True)
    lines=(SOURCE/'train.jsonl').read_text().splitlines()
    original=[json.loads(l) for l in lines]
    groups=defaultdict(list)
    for r in original:
        if r['_meta']['family']=='insufficient':groups[r['_meta']['group_id']].append(r)
    strata=defaultdict(list)
    for group,pair in groups.items():
        assert len(pair)==2
        complete=next(r for r in pair if r['_meta']['pair_role']=='complete')
        absent=next(r for r in pair if r['_meta']['pair_role']!='complete')
        q=complete['questions']['decision']
        role=complete['_meta']['question_option_roles']['decision'][q['label']]
        strata[(complete['_meta']['facts']['scenario'],absent['_meta']['pair_role'],role)].append(group)
    changed=set()
    for stratum,gs in sorted(strata.items()):
        gs=sorted(gs);assert len(gs)%2==0
        random.Random(VERSION+'/'+str(stratum)).shuffle(gs)
        changed.update(gs[:len(gs)//2])
    assert len(changed)==70
    rows=[];output_lines=[];changes=[];balance=Counter();examples={}
    for old,line in zip(original,lines):
        r=copy.deepcopy(old);m=r['_meta'];family=m['family'];modified=m['group_id'] in changed
        if family=='insufficient':
            verify(r)
            if modified:
                r['state']=tree(r['state'],rewrite)
                assert r['state']!=old['state']
                assert tree(r['state'],restore)==old['state']
                restored=copy.deepcopy(r);restored['state']=tree(r['state'],restore);verify(restored)
                m['text_sha256']=digest(r['state'])
                changes.append({'id':m['id'],'group_id':m['group_id'],'scenario':m['facts']['scenario'],
                    'before_sha256':digest(old['state']),'after_sha256':m['text_sha256']})
                examples.setdefault(m['facts']['scenario'],{'before':old['state'],'after':r['state'],'answer':gold(r,'decision')})
            q=r['questions']['decision'];role=m['question_option_roles']['decision'][q['label']]
            balance[(m['facts']['scenario'],m['pair_role'],role,'prose' if modified else 'original')]+=1
        assert r['questions']==old['questions'] and r['_meta']['id']==old['_meta']['id']
        delta=copy.deepcopy(r);delta['state']=old['state'];delta['_meta']['text_sha256']=old['_meta']['text_sha256']
        assert delta==old
        materialize(r);rows.append(r)
        output_lines.append(json.dumps(r,ensure_ascii=False,sort_keys=True) if modified else line)
    assert len(rows)==1500 and len(changes)==140
    assert len({digest(r['state']) for r in rows})==1500
    for scene,pair_role,role,style in list(balance):
        assert balance[(scene,pair_role,role,'original')]==balance[(scene,pair_role,role,'prose')]
    (OUT/'train.jsonl').write_text('\n'.join(output_lines)+'\n')
    (OUT/'development.jsonl').write_bytes((SOURCE/'development.jsonl').read_bytes())
    by_id={r['_meta']['id']:r for r in rows}
    probe=[by_id[json.loads(line)['_meta']['id']] for line in (SOURCE/'train_probe.jsonl').read_text().splitlines()]
    (OUT/'train_probe.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in probe))
    hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['train.jsonl','development.jsonl','train_probe.jsonl']}
    manifest={'status':'candidate_only_not_trained','version':VERSION,'contexts':1500,
        'subquestions':sum(len(r['questions']) for r in rows),'modified_contexts':140,'modified_pairs':70,
        'unchanged_contexts':1360,'unchanged_other_six_families':1220,
        'unchanged_development':336,'hashes':hashes,
        'only_changes':['140 state texts and their corresponding text hashes'],
        'checks':{'questions_and_labels_identical':True,'record_order_and_ids_identical':True,
            'augmentation_seeds_unchanged':True,'inverse_fact_reconstruction_exact':140,
            'all_case_and_rule_values_preserved':True,'style_balanced_within_scenario_pair_role_answer':True},
        'scope':'Same 1500 contexts with 140 wording variants replacing original presentations; not new independent cases. All three retained families remain byte-identical. Training not launched. Tokenization pending.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (OUT/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
    (OUT/'style_balance.json').write_text(json.dumps([{'scenario':s,'pair_role':p,'answer':a,'style':t,'count':n} for (s,p,a,t),n in sorted(balance.items())],ensure_ascii=False,indent=2)+'\n')
    (OUT/'examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n')
    for name in ['preflight.py','evaluate_development.py']:(OUT/name).write_bytes((SOURCE/name).read_bytes())
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
