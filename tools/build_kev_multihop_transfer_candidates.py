#!/usr/bin/env python3
"""270 newly sampled multihop contexts; no training or benchmark generator import."""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date, timedelta
from build_kev_multihop_coverage_candidates import NAMES, nth_supervisor, ownership, verify as prior_verify
from build_targeted_v4_components import ROOT, choice, record
from build_targeted_v5 import digest, graph_decision, NONE
from check_targeted_v4_rules import gold, materialize

BASE = ROOT / 'artifacts/kev_training_eval_20261026'
OUT = BASE / 'multihop_transfer_candidates_20261030'
VERSION = 'multihop-transfer-20261030'
COUNTS = {'dependency_candidates':70, 'rank_escalation':25, 'exact_supervisor_hops':25,
          'dated_roster':60, 'ownership_control_and_profit':90}
TITLES = ['Junior Associate', 'Senior Specialist', 'Team Leader', 'Department Principal', 'Division Head', 'Chief Executive']

def dependency(i, rng):
    nodes=rng.sample(NAMES,14);length=1+i%5;chain=nodes[:length+1];failed=chain[-1]
    edges=[(a,b,True) for a,b in zip(chain,chain[1:])]
    # Hard fan-out, soft barrier with a downstream consumer, and an unrelated branch.
    edges += [(nodes[7],chain[rng.randrange(len(chain))],True),
              (nodes[8],failed,False),(nodes[9],nodes[8],True),
              (failed,nodes[10],True),(nodes[11],nodes[12],True)]
    affected=set(chain+[nodes[7]])
    candidates=rng.sample([n for n in nodes if n not in affected],3)
    if i%3: candidates[rng.randrange(3)]=rng.choice(chain[:-1]+[nodes[7]])
    rng.shuffle(edges)
    lines=[]
    for j,(consumer,prerequisite,hard) in enumerate(edges):
        t='hard' if hard else 'soft';style=(i+j)%3
        lines.append(f'{consumer} requires {prerequisite} through a {t} dependency.' if style==0 else
                     f'{prerequisite} is a {t} prerequisite for {consumer}.' if style==1 else
                     f'Dependency: consumer={consumer}; prerequisite={prerequisite}; kind={t}.')
    state='FAILURE RULE\nA failed hard prerequisite disables its consumer. Apply this rule repeatedly until no further units fail. Soft links never propagate failure. Failure never propagates from a consumer to its prerequisite. All dependencies are listed.\n'+'\n'.join(lines)+f'\nInitial failed unit: {failed}. All other units initially function.'
    answer=next((c for c in candidates if c in affected),NONE)
    q=choice(rng,'After propagation, which listed candidate has failed?',answer,candidates+[NONE])
    # Explicit none must not be augmented into a second duplicate none option.
    q['target']={q['label']:1.0}
    return record('multihop',i,state,{'decision':q},{'edges':edges,'initial':failed,'chain_hops':length,'candidates':candidates},'dependency_candidates','从失败的先决条件沿消费者方向传播，软边阻断。')

def roster(i,rng):
    names=rng.sample(NAMES,12);teams=['Copper','Juniper','Marble'];assets=['Gateway','Recorder','Scheduler','Indexer','Collector']
    route={a:rng.choice(teams) for a in assets};asset=rng.choice(assets);team=route[asset]
    contacts={t:names[j*3:j*3+3] for j,t in enumerate(teams)}
    day=date(2030,rng.randint(1,12),rng.randint(6,22));desired=i%3;leave={};coverage=Counter()
    for t,people in contacts.items():
        for position,p in enumerate(people):
            unavailable=t==team and position<desired
            if unavailable:
                mode=(i//3+position)%3
                start=day if mode==0 else day-timedelta(days=2)
                end=day if mode==1 else day+timedelta(days=3)
                coverage[['start_boundary','end_boundary','inside'][mode]]+=1
            else:
                mode=(i+position+teams.index(t))%3
                if mode==0:coverage['no_absence_record']+=1;continue
                if mode==1:start=day+timedelta(days=1+rng.randrange(4));end=start+timedelta(days=3);coverage['future_absence']+=1
                else:end=day-timedelta(days=1+rng.randrange(4));start=end-timedelta(days=3);coverage['past_absence']+=1
            leave[p]=(start,end)
    lines=[f'The owner of {a} is team {t}.' for a,t in route.items()]
    for t,(primary,backup,lead) in contacts.items():
        lines += [f'{t} primary contact: {primary}.',f'{t} backup contact: {backup}.',f'{t} duty lead: {lead}.']
    lines += [f'Absence for {p}: {a} to {b}, inclusive.' for p,(a,b) in leave.items()]
    rng.shuffle(lines)
    state='DISPATCH POLICY\nRoute the incident to the asset owner. Try the primary contact, then the backup contact, then the duty lead, stopping at the first available person. A person is unavailable exactly on the listed inclusive absence interval and available otherwise. No absence record means available.\n'+'\n'.join(lines)+f'\nAsset needing help: {asset}. Date needing coverage: {day}.'
    answer=contacts[team][desired]
    qs={'contact':choice(rng,'Who receives this incident?',answer,contacts[team]+rng.sample([p for p in names if p not in contacts[team]],2)),
        'group':choice(rng,'Which team owns the incident asset?',team,teams)}
    return record('multihop',i,state,qs,{'desired_contact_position':desired,'absence_coverage':dict(coverage)},'dated_roster','先关联资产与团队，再判断各联系人的日期可用性。')

def rank(i,rng):
    r=graph_decision(i,'rank_escalation',rng)
    for old,new in zip(['Associate','Specialist','Lead','Principal','Head','Executive'],TITLES):
        r['state']=re.sub(r'\b'+old+r'\b',new,r['state'])
    return r

def wrap(state,i):
    lines=state.splitlines()
    if i%3==0:return state
    if i%3==1:return '\n'.join(f'[{j+1}] {line}' for j,line in enumerate(lines))
    return {'document':'Operational case record','entries':lines}

def unwrap(state):
    if isinstance(state,dict):
        assert set(state)=={'document','entries'} and isinstance(state['entries'],list)
        return '\n'.join(state['entries'])
    return '\n'.join(re.sub(r'^\[\d+\] ','',line) for line in state.splitlines())

def verify(row):
    r=copy.deepcopy(row);r['state']=unwrap(r['state']);s=r['state'];kind=r['_meta']['subtype']
    if kind=='dependency_candidates':
        edges=[]
        for line in s.splitlines()[2:-1]:
            m=re.fullmatch(r'(\w+) requires (\w+) through a (hard|soft) dependency\.',line)
            if m:edges.append((m[1],m[2],m[3]));continue
            m=re.fullmatch(r'(\w+) is a (hard|soft) prerequisite for (\w+)\.',line)
            if m:edges.append((m[3],m[1],m[2]));continue
            m=re.fullmatch(r'Dependency: consumer=(\w+); prerequisite=(\w+); kind=(hard|soft)\.',line)
            assert m,line
            edges.append((m[1],m[2],m[3]))
        failed={re.search(r'Initial failed unit: (\w+)',s)[1]}
        for _ in range(len(edges)+1):
            new={a for a,b,t in edges if t=='hard' and b in failed}-failed
            if not new:break
            failed.update(new)
        else:raise AssertionError('Failure closure did not settle')
        answers=set(r['questions']['decision']['criteria'].values())&failed
        assert len(answers)<=1
        assert gold(r,'decision')==(next(iter(answers)) if answers else NONE)
    elif kind=='rank_escalation':
        titles=re.search(r'Ranks in increasing authority: ([^.]+)\.',s)[1].split(', ')
        required=re.search(r'with rank ([^.]+?) or higher',s)[1]
        links=dict(re.findall(r'(\w+) has supervisor (\w+)\.',s))
        ranks=dict(re.findall(r'(\w+) holds rank ([^.]+)\.',s))
        node=re.search(r'Request origin: (\w+)',s)[1];visited=set()
        while node in links:
            node=links[node];assert node not in visited;visited.add(node)
            if titles.index(ranks[node])>=titles.index(required):break
        else:raise AssertionError('No qualifying supervisor')
        assert gold(r,'decision')==node
    elif kind=='dated_roster':
        routes=dict(re.findall(r'The owner of (\w+) is team (\w+)\.',s))
        people={role:dict(re.findall(r'(\w+) '+role+r': (\w+)\.',s)) for role in ['primary contact','backup contact','duty lead']}
        leave={p:(date.fromisoformat(a),date.fromisoformat(b)) for p,a,b in re.findall(r'Absence for (\w+): ([\d-]+) to ([\d-]+), inclusive\.',s)}
        asset=re.search(r'Asset needing help: (\w+)',s)[1];day=date.fromisoformat(re.search(r'Date needing coverage: ([\d-]+)',s)[1]);team=routes[asset]
        contact=next(people[role][team] for role in people if people[role][team] not in leave or not leave[people[role][team]][0]<=day<=leave[people[role][team]][1])
        assert gold(r,'contact')==contact and gold(r,'group')==team
    else:prior_verify(r)
    for q in row['questions'].values():
        if 'target' in q:assert q['target']=={q['label']:1.0}
    materialize(row)

def main():
    OUT.mkdir(exist_ok=True);seen=set()
    paths=list((ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'))+[BASE/'targeted_v6_20261030/train.jsonl',BASE/'targeted_v6_20261030/development.jsonl']
    for path in paths:
        seen.update(digest(json.loads(line)['state']) for line in path.read_text().splitlines())
    manifest={'status':'component_only_not_trained','planned_train_contexts':270,'files':{},'limitations':['Same-author visible-text checker, no external semantic review.','Shared generators and inspected official tests do not support blind generalization claims.','Only the multihop component, not a complete 1500-context corpus.']}
    functions={'dependency_candidates':dependency,'rank_escalation':rank,'exact_supervisor_hops':nth_supervisor,'dated_roster':roster,'ownership_control_and_profit':ownership}
    for split,factor in [('train',1),('development',.2)]:
        rows=[];rejected=0;coverage=Counter()
        for kind,n in COUNTS.items():
            for i in range(int(n*factor)):
                for attempt in range(10000):
                    r=functions[kind](i,random.Random(f'{VERSION}/{split}/{kind}/{i}/{attempt}'));canonical=r['state'];presentation=(i//3)%3;r['state']=wrap(canonical,presentation)
                    assert unwrap(r['state'])==canonical
                    h=digest(r['state']);raw=digest(canonical)
                    if h not in seen and raw not in seen:break
                else:raise AssertionError('Unable to sample a fresh case')
                seen.update([h,raw]);m=r['_meta'];m.update(id=f'{VERSION}/{split}/{kind}/{i}',group_id=f'{VERSION}/{split}/{kind}/{i}',source=VERSION,split=split,text_sha256=h,presentation=['plain','numbered','object'][presentation])
                for q in r['questions'].values():q['src']=VERSION
                verify(r)
                for name,q in r['questions'].items():
                    for wrong in q['criteria']:
                        if wrong==q['label']:continue
                        bad=copy.deepcopy(r);bad['questions'][name]['label']=wrong
                        if 'target' in bad['questions'][name]:bad['questions'][name]['target']={wrong:1.0}
                        try:verify(bad)
                        except AssertionError:rejected+=1
                        else:raise AssertionError(('Wrong label accepted',m['id'],name))
                if kind=='dated_roster':coverage.update(m['facts']['absence_coverage'])
                rows.append(r)
        random.Random(VERSION+split).shuffle(rows);p=OUT/(split+'.candidate.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
        for line in p.read_text().splitlines():verify(json.loads(line))
        layout_labels=Counter()
        for r in rows:
            kind=r['_meta']['subtype'];m=r['_meta']
            if kind=='dependency_candidates':outcome='none' if gold(r,'decision')==NONE else 'failed_candidate'
            elif kind=='dated_roster':outcome=str(m['facts']['desired_contact_position'])
            else:continue
            layout_labels[kind+'/'+outcome+'/'+m['presentation']]+=1
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'subtypes':dict(Counter(r['_meta']['subtype'] for r in rows)),'absence_coverage':dict(coverage),'layout_by_outcome':dict(layout_labels),'incorrect_labels_rejected':rejected,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        (OUT/(split+'.examples.json')).write_text(json.dumps([next(r for r in rows if r['_meta']['subtype']==k) for k in COUNTS],ensure_ascii=False,indent=2)+'\n')
    manifest['checks']={'visible_label_recomputation':True,'serialized_roundtrip_verified':True,'normalized_state_train_dev_prior_v6_and_frozen_test_overlap':0}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
