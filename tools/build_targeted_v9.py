#!/usr/bin/env python3
"""1500 base contexts plus separately counted matched counterfactual views."""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path
import build_kev_matched_candidates as gen
from build_targeted_v5 import digest
from check_targeted_v4_rules import gold, materialize

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'targeted_v9_matched_20261030'
OLD=BASE/'targeted_v7_20261030'
VERSION='targeted-v9-matched-20261030'
RETAINED={'tool_routing','temporal','injection'}
PROB={'table':75,'bayes':60,'all':40,'any_fail':50,'any':25,'compare':40,'expected_value':60}
MULTI={'dependency_candidates':90,'ownership_control_and_profit':70,'dated_roster':60,'rank_escalation':25,'exact_supervisor_hops':25}
POLICY={'pay_loss':60,'pay_limit':50,'pay_sublimit':50,'not_purchased':18,'waiting':18,'late':16,'threshold':16,'flag':16,'intentional':16,'legal_zero':40}
POLICY_DEV={'pay_loss':12,'pay_limit':10,'pay_sublimit':10,'not_purchased':4,'waiting':4,'late':3,'threshold':3,'flag':3,'intentional':3,'legal_zero':8}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def visible_verify(row):
    r=copy.deepcopy(row);family=r['_meta']['family'];r['_meta']['facts']={}
    if family=='probability':
        if r['_meta']['subtype']=='table':
            mat=gen.prob.read_table(r['state']);row_name,col=re.search(r'Among records from (.+), what percentage have status (.+)\?',r['questions']['forward']['instructions']).groups()
            r['_meta']['facts']={'target_row':row_name,'target_status':col,'target_row_position':list(mat).index(row_name),'target_status_position':list(next(iter(mat.values()))).index(col)}
        gen.verify_probability(r)
    elif family=='policy':gen.policy.verify(r)
    elif family=='insufficient':gen.insuff.verify(r)
    elif family=='multihop':gen.multi.verify(r)
    else:materialize(r)

def answer(row,qid):
    q=row['questions'][qid]
    return gold(row,qid) if q['type']=='choice' else q['label']

def policy_structure(row):
    f=row['_meta']['facts'];covers=len(re.findall(r'\[Cover C\d+\]',row['state']))
    return '/'.join(map(str,[f['domain'],covers,f['money_scale']]))

def create(family,kind,i,split,rng):
    if family=='probability':return gen.probability_pair(i,kind,rng)
    if family=='policy':return gen.policy_pair(i,kind,rng)
    if family=='insufficient':
        scene,variant=kind.split('/');return gen.insufficient_pair(scene,i,variant,rng)
    if kind=='dependency_candidates':return gen.dependency_pair(i,rng,split)
    fn={'ownership_control_and_profit':gen.multi.ownership,'dated_roster':gen.multi.roster,'rank_escalation':gen.multi.rank,'exact_supervisor_hops':gen.multi.nth_supervisor}[kind]
    a=fn(i,rng);return a,None,'single'

def main():
    assert not (OUT/'launch.json').exists() and not (OUT/'run_status.json').exists(),'Cannot rebuild a launched experiment'
    OUT.mkdir(exist_ok=True);seen=set();prior=set();frozen=set();splits={};pair_maps={};retained_lines={}
    sources={}
    for path in list((ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl')):
        frozen.update(digest(json.loads(l)['state']) for l in path.read_text().splitlines())
    for folder in ['targeted_v5_20261030','targeted_v6_20261030','targeted_v7_20261030','targeted_v8_steps_20261030']:
        for fn in ['train.jsonl','development.jsonl']:
            path=BASE/folder/fn;sources[str(path.relative_to(BASE))]=sha(path)
            prior.update(digest(json.loads(l)['state']) for l in path.read_text().splitlines())
    manifest={'version':VERSION,'status':'building','goal_achieved':False,'replay_records_separate':6000,'files':{},'source_hashes':sources,
              'training_plan':{'init':'original pre-targeted stage3','epochs':1,'seed':101,'lr':1e-5,'lora':16,'batch':4,'accum':2,'replay':6000},
              'limitations':['1500 base groups are distinct visible cases, not a claim of statistical independence across shared templates.','Matched views are additional training exposures, not independent new base cases.','Choice targets are one-hot to preserve the matched candidate semantics under augmentation; this changes augmentation exposure as well as data.','Same-author visible-text verification is not independent external review.','Official diagnostic tests informed design; future evaluation is not blind confirmation.','Policy development reserves domain/cover-count/money-scale combinations, graph development adds side branches. Other families use disjoint case groups from shared generators.']}
    structure_sets={}
    for split in ['train','development']:
        factor=1 if split=='train' else .2
        original=(OLD/(split+'.jsonl')).read_text().splitlines()
        retained={json.loads(l)['_meta']['id']:l for l in original if json.loads(l)['_meta']['family'] in RETAINED};retained_lines[split]=retained
        parents=[json.loads(l) for l in retained.values()];views=[];mapping=[];retries=Counter();policy_keys=set()
        groups={'probability':{k:int(n*factor) for k,n in PROB.items()},'multihop':{k:int(n*factor) for k,n in MULTI.items()},'policy':POLICY if split=='train' else POLICY_DEV,
                'insufficient':{scene+'/'+variant:n for scene in gen.insuff.SCENARIOS for variant,n in ({'yes':10,'no':10,'unknown':12,'nondeciding':8} if split=='train' else {'yes':2,'no':2,'unknown':3,'nondeciding':3}).items()}}
        for family,counts in groups.items():
            for kind,n in counts.items():
                for j in range(n):
                    for attempt in range(5000):
                        rng=random.Random(f'{VERSION}/{split}/{family}/{kind}/{j}/{attempt}')
                        # No label or evaluated result is consulted when drawing.
                        index=j if family!='policy' else rng.randrange(1000000)
                        try:a,b,mutation=create(family,kind,index,split,rng)
                        except ValueError as exc:
                            retries[str(exc)]+=1;continue
                        candidates=[a]+([b] if b is not None else [])
                        hs=[digest(r['state']) for r in candidates]
                        if len(set(hs))!=len(hs) or any(h in seen|prior|frozen for h in hs):retries['duplicate_visible_state']+=1;continue
                        structure=None
                        if family=='policy':
                            structure=policy_structure(a);assert structure==policy_structure(b)
                            reserved=int(hashlib.sha256(structure.encode()).hexdigest(),16)%4==0
                            if reserved!=(split=='development'):retries['reserved_policy_combination']+=1;continue
                        break
                    else:raise AssertionError(('Cannot fill stratum',split,family,kind,j,retries))
                    group=f'{VERSION}/{split}/{family}/{kind}/{j}'
                    for role,r in [('base',a)]+([('matched',b)] if b is not None else []):
                        r['_meta'].update(id=group+'/'+role,group_id=group,source=VERSION+'/'+family,split=split,view_role=role,parent_stratum=kind,mutation=mutation,text_sha256=digest(r['state']),
                                          review_zh='标签由可见规则复算；配对视图固定问题与候选，按事实决定是否改变答案。')
                        if structure:r['_meta']['group_structure_key']=structure
                        for q in r['questions'].values():q['src']=VERSION+'/'+family
                        visible_verify(r)
                    parents.append(a)
                    if b is not None:
                        views.append(b)
                        changed=[q for q in a['questions'] if answer(a,q)!=answer(b,q)]
                        for qid in a['questions']:
                            x,y=a['questions'][qid],b['questions'][qid]
                            assert {k:v for k,v in x.items() if k not in ['label','target']}=={k:v for k,v in y.items() if k not in ['label','target']}
                        mapping.append({'group_id':group,'family':family,'parent_stratum':kind,'base_id':a['_meta']['id'],'matched_id':b['_meta']['id'],'mutation':mutation,'changed_questions':changed,
                                        'unchanged_questions':[q for q in a['questions'] if q not in changed]})
                    seen.update(hs)
                    if structure:policy_keys.add(structure)
            print(split,family,'base_so_far',len(parents),'matched_so_far',len(views),flush=True)
        assert len(parents)==(1500 if split=='train' else 344)
        assert len(views)==(1020 if split=='train' else 218)
        assert Counter(r['_meta']['family'] for r in parents)==({'tool_routing':100,'temporal':100,'injection':100,'probability':350,'multihop':270,'policy':300,'insufficient':280} if split=='train' else {'tool_routing':30,'temporal':30,'injection':30,'probability':70,'multihop':54,'policy':60,'insufficient':70})
        allrows=parents+views
        assert len({r['_meta']['id'] for r in allrows})==len(allrows)
        hashes=[digest(r['state']) for r in allrows];assert len(hashes)==len(set(hashes)) and not set(hashes)&frozen
        # Exhaustive wrong-label mutations, including consistent target changes.
        rejected=0
        for r in allrows:
            if r['_meta']['family'] in RETAINED:continue
            for qid,q in r['questions'].items():
                wrongs=[not q['label']] if q['type']=='noul' else [k for k in (range(len(q['criteria'])) if q['type']=='score' else q['criteria']) if k!=q['label']]
                for wrong in wrongs:
                    bad=copy.deepcopy(r);bq=bad['questions'][qid];bq['label']=wrong
                    if 'target' in bq:bq['target']={wrong:1.0}
                    try:visible_verify(bad)
                    except AssertionError:rejected+=1
                    else:raise AssertionError(('Wrong label accepted',r['_meta']['id'],qid,wrong))
        for suffix,rows in [('_base',parents),('',allrows)]:
            rng=random.Random(VERSION+'/'+split+suffix);rng.shuffle(rows)
            # Original three categories retain their exact serialized lines.
            lines=[retained[r['_meta']['id']] if r['_meta']['family'] in RETAINED else json.dumps(r,ensure_ascii=False,sort_keys=True) for r in rows]
            path=OUT/(split+suffix+'.jsonl');path.write_text('\n'.join(lines)+'\n')
            for line in path.read_text().splitlines():visible_verify(json.loads(line))
            assert {json.loads(l)['_meta']['id']:l for l in lines if json.loads(l)['_meta']['family'] in RETAINED}==retained
            manifest['files'][split+suffix]={'records':len(rows),'questions':sum(len(r['questions']) for r in rows),'sha256':sha(path)}
        pair_maps[split]=mapping;splits[split]=parents;structure_sets[split]=policy_keys
        manifest[split]={'base_context_groups':len(parents),'additional_matched_views':len(views),'retained_byte_identical':len(retained),'wrong_label_mutations_rejected':rejected,
                         'pairs_with_any_changed_answer':sum(bool(x['changed_questions']) for x in mapping),'pairs_with_all_answers_unchanged':sum(not x['changed_questions'] for x in mapping),
                         'mutation_counts':dict(Counter(x['mutation'] for x in mapping)),'resampling_reasons':dict(retries),'reserved_policy_structure_keys':sorted(policy_keys)}
    assert not structure_sets['train']&structure_sets['development']
    train_ids={r['_meta']['group_id'] for r in splits['train']};dev_ids={r['_meta']['group_id'] for r in splits['development']};assert not train_ids&dev_ids
    probe=[]
    for family in sorted({r['_meta']['family'] for r in splits['train']}):
        pool=[r for r in splits['train'] if r['_meta']['family']==family]
        probe.extend(random.Random(VERSION+'/probe/'+family).sample(sorted(pool,key=lambda r:r['_meta']['id']),20))
    path=OUT/'train_probe.jsonl';path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in probe));manifest['files']['train_probe']={'records':140,'questions':sum(len(r['questions']) for r in probe),'sha256':sha(path)}
    (OUT/'pair_mapping.json').write_text(json.dumps(pair_maps,ensure_ascii=False,indent=2)+'\n')
    examples=[]
    lookup={r['_meta']['id']:r for r in map(json.loads,(OUT/'train.jsonl').read_text().splitlines())}
    for family in ['probability','multihop','policy','insufficient']:
        for changed in [True,False]:
            pair=next(x for x in pair_maps['train'] if x['family']==family and bool(x['changed_questions'])==changed)
            examples.append({'pair':pair,'records':[lookup[pair['base_id']],lookup[pair['matched_id']]]})
    (OUT/'matched_examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n')
    manifest.update(status='assembled_visible_checks_passed_remote_preflight_pending',checks={'retained_three_families_byte_identical':True,'pair_questions_and_candidate_orders_identical':True,'new_visible_states_exclude_prior_and_official_states':True,'train_dev_groups_disjoint':True,'policy_reserved_combinations_disjoint':True,'labels_rechecked_without_latent_facts':True})
    manifest['training_plan']['expected_records_including_replay']=manifest['files']['train']['records']+6000
    manifest['training_plan']['expected_optimizer_steps']=(manifest['training_plan']['expected_records_including_replay']+7)//8
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'files':manifest['files'],'train':manifest['train'],'development':manifest['development']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
