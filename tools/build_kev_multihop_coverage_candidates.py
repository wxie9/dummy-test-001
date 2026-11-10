#!/usr/bin/env python3
"""Additional authored mechanisms discovered missing from v5 coverage.
Candidates only: never overwrite the running v5 corpus or launch training.
"""
import json
import random
import re
from datetime import date, timedelta
from fractions import Fraction as F
from collections import Counter
from pathlib import Path
from build_targeted_v4_components import ROOT, dump, record, choice, percent
from check_targeted_v4_rules import materialize, gold
from build_targeted_v5 import digest

OUT=ROOT/'artifacts/kev_training_eval_20261026/multihop_coverage_candidates_20261030'
VERSION='multihop-coverage-candidate-20261030'
NAMES=['Alder','Beryl','Coral','Delta','Ember','Fjord','Garnet','Hazel','Indigo','Jasper','Kestrel','Lagoon','Mallow','Nimbus','Onyx','Prairie','Quartz','Rowan','Sienna','Topaz','Umber','Violet','Wren','Yarrow','Zenith']
NONE='No ultimate controller'

def nth_supervisor(i,rng):
    names=rng.sample(NAMES,12);chain=names[:rng.randint(5,8)];n=rng.choice([2,3,4])
    edges=list(zip(chain,chain[1:]))+[(names[8],names[9]),(names[10],chain[2])]
    rng.shuffle(edges)
    s=f'ROUTING INSTRUCTION\nFor this request, start at {chain[0]} and follow exactly {n} supervisor links. The person reached must approve; rank and availability do not alter this rule.\n'
    s+='\n'.join(f'{a} has supervisor {b}.' for a,b in edges)
    q=choice(rng,'Who is the required approver?',chain[n],chain[1:]+names[8:10])
    return record('multihop',i,s,{'approver':q},{'start':chain[0],'edges':edges,'steps':n},'exact_supervisor_hops',f'沿主管边走{n}次，终点{chain[n]}。')

def dated_roster(i,rng):
    people=rng.sample(NAMES,12);teams=['Cinder','Mosaic','Tundra'];assets=['SensorA','ValveB','MeterC','RelayD','PanelE','ActuatorF']
    day=date(2029,rng.randint(1,12),rng.randint(5,23));route={a:rng.choice(teams) for a in assets}
    selected=rng.choice(assets);team=route[selected];roster={t:people[3*j:3*j+3] for j,t in enumerate(teams)}
    desired=i%3;leave={};lines=[]
    for t in teams:
        for j,p in enumerate(roster[t]):
            unavailable=(t==team and j<desired) or (t!=team and rng.choice([True,False]))
            start=day-timedelta(days=rng.randint(0,3)) if unavailable else day+timedelta(days=rng.randint(1,5))
            end=start+timedelta(days=rng.randint(3,7))
            leave[p]=(start,end)
        lines.append(f'Group {t}: first contact {roster[t][0]}; backup {roster[t][1]}; duty lead {roster[t][2]}.')
    # Ensure selected lead is available on the incident day if reached.
    if desired==2:leave[roster[team][2]]=(day+timedelta(days=1),day+timedelta(days=4))
    lines += [f'{asset} belongs to group {owner}.' for asset,owner in route.items()]
    lines += [f'{p} is unavailable from {a} through {b}, both dates included.' for p,(a,b) in leave.items()]
    rng.shuffle(lines)
    s='MAINTENANCE DISPATCH\nFirst identify the asset\'s group. Contact its first contact if available on the incident date; otherwise try the backup, then the duty lead. Only the stated absence interval makes a person unavailable. A person is available on all other dates. At least one of that group\'s three contacts is available.\n'+'\n'.join(lines)+f'\nIncident asset: {selected}. Incident date: {day}.'
    answer=next(p for p in roster[team] if not leave[p][0]<=day<=leave[p][1])
    assert answer==roster[team][desired]
    qs={'contact':choice(rng,'Which person must be contacted?',answer,roster[team]+rng.sample([p for p in people if p not in roster[team]],2)),
        'group':choice(rng,'Which group owns the incident asset?',team,teams)}
    return record('multihop',i,s,qs,{'routes':route,'roster':roster,'leave':{p:[str(a),str(b)] for p,(a,b) in leave.items()},'incident_date':str(day),'selected':selected},'dated_roster','先查资产归属，再按当天缺勤区间依次选择人员。')

def ultimate(stakes,target):
    entities=set(stakes)|{h for owners in stakes.values() for h in owners}
    controlled={e:{e} for e in entities}
    for e in entities:
        while True:
            added={child for child,owners in stakes.items() if sum(v for h,v in owners.items() if h in controlled[e])>50}
            new=controlled[e]|added
            if new==controlled[e]:break
            controlled[e]=new
    controllers={e for e in entities if e!=target and target in controlled[e]}
    roots=[e for e in controllers if not any(e in controlled[other] for other in controllers-{e})]
    assert len(roots)<=1,(stakes,roots)
    return roots[0] if roots else NONE

def economic(stakes,owner,target):
    # Expand every ownership path, counting direct interest plus products.
    def interest(child,seen):
        assert child not in seen
        return sum(F(v,100)*(1 if h==owner else interest(h,seen|{child})) for h,v in stakes.get(child,{}).items())
    return interest(target,set())

def ownership(i,rng):
    top,a,b,target,rival=rng.sample(NAMES,5)
    if i%2==0:
        p=rng.choice([40,50,51,60,75,85]);q=rng.choice([35,50,51,65,80])
        stakes={a:{top:p},target:{a:q,rival:100-q}}
        shape='chain'
    else:
        p1=rng.choice([40,51,65,80]);p2=rng.choice([40,50,60,75,90])
        d=rng.choice([0,5,10]);x=rng.choice([20,25,30,35,40]);y=rng.choice([20,25,30,35,40])
        stakes={a:{top:p1},b:{top:p2},target:{a:x,b:y,top:d,rival:100-x-y-d}}
        shape='aggregated'
    answer=ultimate(stakes,target);profit=economic(stakes,top,target)
    lines=[f'{holder} owns {percent(F(v,100))} of {child}.' for child,owners in stakes.items() for holder,v in owners.items() if v]
    rng.shuffle(lines)
    s='CORPORATE HOLDINGS REGISTER\nControl and profit share are different. An entity controls an issuer when its own voting shares plus voting shares held by issuers it already controls exceed 50%. Exactly 50% is insufficient. Repeat this rule until no new controlled issuers are found. The ultimate controller is a controller that is not itself controlled by another controller of the target. Profit share instead adds the products of share percentages along all ownership paths. No external agreements confer control. Unlisted shares are dispersed among unrelated investors, each holding less than 5%; they do not act together. Unlisted ownership links do not exist.\n'+'\n'.join(lines)
    qs={'controller':choice(rng,f'Who is the ultimate controller of {target}?',answer,[top,a,b,rival,NONE]),
        'interest':choice(rng,f'What is {top}\'s economic interest in {target}? Round to two decimal places.',percent(profit),[percent(1-profit),'0.00%','50.00%','100.00%',percent(min(F(1),profit+F(1,20)))])}
    return record('multihop',i,s,qs,{'stakes':stakes,'target':target,'economic_owner':top,'shape':shape},'ownership_control_and_profit',f'控制权闭包结果{answer}；经济收益比例{percent(profit)}。')

def verify(r):
    s=r['state'];kind=r['_meta']['subtype']
    if kind=='exact_supervisor_hops':
        start,n=re.search(r'start at (\w+) and follow exactly (\d+) supervisor links',s).groups()
        links=dict(re.findall(r'(\w+) has supervisor (\w+)\.',s));node=start
        for _ in range(int(n)):node=links[node]
        assert gold(r,'approver')==node
    elif kind=='dated_roster':
        roster={t:[a,b,c] for t,a,b,c in re.findall(r'Group (\w+): first contact (\w+); backup (\w+); duty lead (\w+)\.',s)}
        routes=dict(re.findall(r'(\w+) belongs to group (\w+)\.',s))
        leave={p:(date.fromisoformat(a),date.fromisoformat(b)) for p,a,b in re.findall(r'(\w+) is unavailable from ([\d-]+) through ([\d-]+), both dates included',s)}
        asset,when=re.search(r'Incident asset: (\w+)\. Incident date: ([\d-]+)',s).groups();day=date.fromisoformat(when)
        group=routes[asset];answer=next(p for p in roster[group] if not leave[p][0]<=day<=leave[p][1])
        assert gold(r,'contact')==answer and gold(r,'group')==group
    else:
        stakes={}
        for owner,p,child in re.findall(r'(\w+) owns ([\d.]+)% of (\w+)\.',s):stakes.setdefault(child,{})[owner]=F(p)
        target=re.search(r'controller of (\w+)',r['questions']['controller']['instructions'])[1]
        owner=re.search(r'What is (\w+)\x27s economic interest',r['questions']['interest']['instructions'])[1]
        # A second implementation uses transitive control edges and enumerates
        # simple ownership paths rather than the generator's recursive expansion.
        nodes=set(stakes)|{h for d in stakes.values() for h in d};control=set()
        while True:
            grown=control|{(e,c) for e in nodes for c,owners in stakes.items() if c!=e and sum(v for h,v in owners.items() if h==e or (e,h) in control)>50}
            if grown==control:break
            control=grown
        controllers={e for e,c in control if c==target}
        roots=[e for e in controllers if not any((o,e) in control for o in controllers-{e})]
        assert len(roots)<=1
        value=F(0);stack=[(target,F(1),frozenset())]
        while stack:
            c,p,seen=stack.pop();assert c not in seen
            for h,v in stakes.get(c,{}).items():
                fraction=p*v/100
                if h==owner:value+=fraction
                else:stack.append((h,fraction,seen|{c}))
        assert gold(r,'controller')==(roots[0] if roots else NONE)
        assert gold(r,'interest')==percent(value)

def main():
    OUT.mkdir(exist_ok=True)
    # Exclude exact visible states already used anywhere in prior local targeted
    # corpora and frozen official tests. This is not a semantic holdout guarantee.
    seen=set()
    paths=list((ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'))
    for version in ['targeted_v4_20261030','targeted_v5_20261030']:
        paths+=list((OUT.parent/version).glob('*.jsonl'))
    for p in paths:
        for line in p.read_text().splitlines():
            r=json.loads(line)
            if 'state' in r:seen.add(digest(r['state']))
    manifest={'status':'candidate_only_not_used_for_training','files':{},'purpose':'Cover exact-hop routing, dated roster joins and aggregated control/economic-interest mechanisms missing from v5.',
        'scope':'Same-author independent visible-text checker. These are new draws, not independent generalization proof. Running v5 inputs are unchanged.'}
    for split,mult in [('train',1),('development',.2)]:
        rows=[]
        for name,fn,n in [('exact_supervisor_hops',nth_supervisor,30),('dated_roster',dated_roster,60),('ownership_control_and_profit',ownership,90)]:
            made=0;attempt=0
            while made<int(n*mult):
                attempt+=1;assert attempt<10000
                r=fn(made,random.Random(f'{VERSION}/{split}/{name}/{attempt}'))
                h=digest(r['state'])
                if h in seen:continue
                verify(r);materialize(r);seen.add(h)
                m=r['_meta'];m['id']=f'{VERSION}/{split}/{name}/{made:05d}';m['group_id']=m['id'];m['split']=split;m['source']=VERSION;m['text_sha256']=h
                for q in r['questions'].values():q['src']=VERSION
                rows.append(r);made+=1
        p=OUT/(split+'.candidate.jsonl');p.write_text(''.join(dump(r)+'\n' for r in rows))
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'subtypes':dict(Counter(r['_meta']['subtype'] for r in rows))}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
