#!/usr/bin/env python3
"""New authored probability/graph components. No benchmark generator imports.

Intermediate components, not an assembled or approved training set.
"""
import hashlib
import json
import random
from collections import Counter
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/kev_training_eval_20261026/targeted_v4_20261030'
VERSION='targeted-v4-20261030'

def dump(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
def percent(x):return f'{float(100*x):.2f}%'
def cash(x):return ('-' if x<0 else '')+f'${abs(float(x)):.2f}'

def choice(rng,prompt,gold,others):
    opts=list(dict.fromkeys([gold]+others));rng.shuffle(opts)
    assert len(opts)>=3
    criteria={chr(97+i):v for i,v in enumerate(opts)}
    return {'type':'choice','instructions':prompt,'criteria':criteria,
            'label':next(k for k,v in criteria.items() if v==gold),'src':VERSION}

def record(family,index,state,questions,facts,subtype,explanation):
    return {'state':state,'questions':questions,'_meta':{
        'id':f'{VERSION}/{family}/candidate/{index:05}',
        'source':VERSION+'_'+family,'family':family,'split':'candidate',
        'group_id':f'{VERSION}/{family}/g{index:05}', 'subtype':subtype,
        'facts':facts,'review_zh':explanation,
        'text_sha256':hashlib.sha256(dump(state).encode()).hexdigest()}}

def numq(rng,prompt,p):
    wrong=[percent(1-p),'0.00%','25.00%','50.00%','75.00%','100.00%']
    return choice(rng,prompt+' Give a percentage rounded to two decimal places.',percent(p),
                  [v for v in wrong if v!=percent(p)][:4])

def probability(index,kind,rng):
    facts={'mechanism':kind};qs={}
    if kind=='table':
        a,b,c,d=[rng.randint(10,190) for _ in range(4)]
        first,second,yes,no=rng.choice([
            ('North depot','South depot','returned','kept'),
            ('Supplier R','Supplier S','defective','acceptable'),
            ('Morning shift','Evening shift','late','on time'),
            ('Coastal branch','Inland branch','renewed','not renewed')])
        if index%2:
            state=f'{first} records {a} items classified as {yes} and {b} as {no}. {second} records {c} as {yes} and {d} as {no}. These groups partition the entire audit; each item belongs to exactly one group and one outcome.'
        else:
            state=f'Complete audit (each item counted once):\n| Origin | {yes} | {no} |\n| {first} | {a} | {b} |\n| {second} | {c} | {d} |'
        qs['reverse']=numq(rng,f'An item is chosen uniformly among all {yes} items. What is the probability its origin is {first}?',F(a,a+c))
        qs['forward']=numq(rng,f'An item is chosen uniformly among all items from {first}. What is the probability it is {yes}?',F(a,a+b))
        facts.update(counts=[a,b,c,d]);note=f'正向 {a}/({a}+{b})；反向 {a}/({a}+{c})，两个条件集合不同。'
    elif kind=='bayes':
        prevalence=rng.choice([1,2,4,8,12,20,35]);sensitivity=rng.choice([70,80,85,90,95]);false=rng.choice([2,5,10,15,25])
        context,positive=rng.choice([('automated defect inspection','defective'),('login-risk screening','malicious'),('spam screening','spam'),('shipment delay warnings','late')])
        state=f'In {context}, {prevalence}% of cases are actually {positive}. Among actually {positive} cases, the system flags {sensitivity}%. Among cases that are not {positive}, it flags {false}%. Select a case uniformly from those flagged. The rates describe this same population.'
        p=F(prevalence*sensitivity,prevalence*sensitivity+(100-prevalence)*false)
        qs['posterior']=numq(rng,f'What is the probability that this flagged case is actually {positive}?',p)
        qs['more_likely']={'type':'noul','instructions':f'Given a flag, is being {positive} strictly more likely than not being {positive}?','label':p>F(1,2),'src':VERSION}
        bounds=rng.choice([[0,10,30,50,70,90,100],[0,20,40,60,80,100]])
        bins=[f'[{l}%, {u}%' + (']' if u==100 else ')') for l,u in zip(bounds,bounds[1:])]
        qs['bucket']={'type':'score','instructions':'Select the interval containing the exact posterior probability. [ includes an endpoint, ) excludes it.','criteria':bins,'label':next(i for i,(l,u) in enumerate(zip(bounds,bounds[1:])) if l<=p*100<u or u==100 and p*100==100),'src':VERSION}
        facts.update(prevalence=prevalence,sensitivity=sensitivity,false_positive=false)
        note=f'后验={prevalence*sensitivity}/({prevalence*sensitivity}+{(100-prevalence)*false})={percent(p)}。'
    elif kind in ('all','any_fail','any'):
        probabilities=[rng.choice([20,35,40,50,60,70,75,80,90,95]) for _ in range(rng.randint(2,5))]
        noun=rng.choice(['delivery routes','independent processing jobs','backup links','inspection stations'])
        state=f'The following {noun} have independent success events, including mutual independence across every subset. Their success rates are '+', '.join(f'{v}%' for v in probabilities)+'. There are no other components.'
        allp=F(1);nonep=F(1)
        for v in probabilities:allp*=F(v,100);nonep*=1-F(v,100)
        p={'all':allp,'any_fail':1-allp,'any':1-nonep}[kind]
        prompt={'all':'What is the probability every component succeeds?','any_fail':'What is the probability at least one component fails?','any':'What is the probability at least one component succeeds?'}[kind]
        qs['probability']=numq(rng,prompt,p)
        facts['probabilities']=probabilities;note=f'{kind}：成功率列表{probabilities}，答案{percent(p)}；any_fail是全部成功的补集。'
    elif kind=='compare':
        p,q=[F(rng.choice([20,25,40,50,60,75,80]),100) for _ in range(2)]
        op=rng.choice(['AND','OR']);first=p*q if op=='AND' else 1-(1-p)*(1-q)
        relation=['lower','equal','higher'][index%3]
        delta=min(F(1,20),first/2,(1-first)/2)
        second=first+({'lower':1,'equal':0,'higher':-1}[relation])*delta
        # All displayed probabilities are exact terminating decimals for these draws.
        assert F(percent(second).strip('%'))/100==second
        state=f'A and B are independent, with probabilities {percent(p)} and {percent(q)}. Event X means '+('both A and B happen' if op=='AND' else 'at least one of A and B happens')+f'. Event Y has probability {percent(second)}. Compare marginal probabilities only; dependence between X and Y is irrelevant.'
        options={'lower':'Y is more likely','equal':'They have equal probabilities','higher':'X is more likely'}
        qs['decision']=choice(rng,'Which statement is correct?',options[relation],list(options.values()))
        facts.update(p=str(p),q=str(q),op=op,second=str(second));note=f'X={percent(first)}，Y={percent(second)}；{relation}。'
    else:
        projects={};ev={};lines=['Choose exactly one project to maximize expected net cash flow, even if all choices have negative expectation. Each project pays its upfront cost exactly once. Outcomes within each project are exhaustive and mutually exclusive; gains and losses exclude that cost.']
        for name in rng.sample(['Birch','Cedar','Maple','Elm','Oak','Pine'],rng.randint(2,4)):
            weights=rng.choice([[25,75],[40,60],[20,30,50],[10,20,30,40]])
            values=[rng.randint(-18,24)*25 for _ in weights]
            if index%4==0:values=[-abs(v)-25 for v in values]
            cost=rng.randint(1,12)*10
            projects[name]={'weights':weights,'values':values,'cost':cost}
            ev[name]=sum(F(w,100)*v for w,v in zip(weights,values))-cost
            terms=[f'{w}%: '+('gain ' if v>=0 else 'lose ')+cash(abs(v)) for w,v in zip(weights,values)]
            lines.append(f'{name}: upfront cost {cash(cost)}; '+ '; '.join(terms)+'.')
        best=max(ev.values());winners=[k for k,v in ev.items() if v==best]
        if len(winners)!=1:return None
        winner=winners[0];state='\n'.join(lines)
        qs['project']=choice(rng,'Which project maximizes expected net cash flow?',winner,list(ev)+['All projects tie'])
        asked=rng.choice(list(ev));v=ev[asked]
        qs['value']=choice(rng,f'What is the expected net cash flow of {asked}?',cash(v),[cash(v+projects[asked]['cost']),cash(-v),cash(v+25),cash(v-25)])
        facts['projects']=projects;facts['asked']=asked;note='按概率加权带符号收益，减一次成本：'+str({k:float(v) for k,v in ev.items()})+'；选择'+winner+'。'
    return record('probability',index,state,qs,facts,kind,note)

def graph(index,kind,rng):
    names=rng.sample(['Aster','Birch','Cedar','Drift','Elm','Flint','Grove','Harbor','Iris','Juniper','Kite','Larch','Moss','North','Oak','Pine','Quarry','Reed','Spruce','Tide'],12)
    path=names[:rng.randint(4,7)];noise=names[7:]
    parents=dict(zip(path,path[1:]));parents[noise[0]]=noise[1]
    links=list(parents.items());rng.shuffle(links)
    if kind=='escalation':
        available={n:rng.choice([True,False]) for n in names};authorized={n:rng.choice([True,False]) for n in names}
        available[path[-1]]=authorized[path[-1]]=True
        if index%4:
            for node in path[1:3]:available[node]=False
        # Earlier nodes may be skipped for different reasons; answer is not always last.
        answer=next(n for n in path[1:] if available[n] and authorized[n])
        state=f'A case starts at {path[0]}. Follow successor links, stopping at the FIRST successor who is both available and authorized for this case. Never select someone outside the chain.\n'
        state+='\n'.join(f'{a} escalates to {b}.' for a,b in links)+'\n'
        attrs=names[1:];rng.shuffle(attrs)
        state+='\n'.join(f'{n}: '+('available' if available[n] else 'unavailable')+'; '+('authorized' if authorized[n] else 'not authorized')+'.' for n in attrs)
        question='Who handles the case?';options=path[1:]+noise[:2]
        facts={'path':path,'parents':parents,'available':available,'authorized':authorized}
    elif kind=='dependency':
        failed=rng.choice(path[1:]);affected=path[:path.index(failed)+1]
        # X depends on Y, so Y's failure propagates towards X, not away from X.
        state='Each listed dependency is mandatory, and no unlisted dependencies exist. X depends on Y means failure of Y makes X unavailable. Failure does not propagate from X to Y. There is no backup.\n'
        state+='\n'.join(f'{a} depends on {b}.' for a,b in links)+f'\nInitially only {failed} is unavailable. All other services initially work.'
        answer=', '.join(sorted(affected));question='Which is the complete set of unavailable services after propagation, including the initial failure?'
        options=[answer,', '.join(sorted(path[path.index(failed):])),failed,', '.join(sorted(path)),', '.join(sorted(affected+noise[:1]))]
        facts={'edges':parents,'failed':failed,'affected':affected}
    else:
        percentages=[rng.choice([40,50,51,60,75,90]) for _ in path[1:]]
        if index%3:
            percentages[:2]=[rng.choice([51,60,75,90]) for _ in range(2)]
        chain=[path[0]]
        for node,p in zip(path[1:],percentages):
            if p<=50:break
            chain.append(node)
        answer=chain[-1]
        state='A direct controller must own strictly more than 50% of voting shares. Control follows successive qualifying links; do not multiply percentages. Exactly 50% does not qualify. The ultimate controller is the last entity reached; if there is no qualifying owner, return the starting company itself. All unlisted shares are dispersed, with no controlling individual.\n'
        ownership=[f'{b} owns {p}% of {a}.' for (a,b),p in zip(zip(path,path[1:]),percentages)]
        ownership.append(f'{noise[1]} owns 90% of {noise[0]}.');rng.shuffle(ownership)
        state+='\n'.join(ownership);question=f'Who is the ultimate controller of {path[0]} under these rules?'
        options=path+noise[:1];facts={'path':path,'percentages':percentages,'qualifying_chain':chain}
    q=choice(rng,question,answer,options)
    return record('multihop',index,state,{'decision':q},facts,kind,'由完整关系及条件求解，正确答案：'+answer+'。')

def main():
    OUT.mkdir(exist_ok=True);components=OUT/'components';components.mkdir(exist_ok=True)
    specs={'probability':{'table':50,'bayes':50,'all':50,'any_fail':50,'any':25,'compare':50,'expected_value':75},
           'multihop':{'escalation':90,'dependency':90,'ownership':90}}
    coverage={}
    for family,quotas in specs.items():
        rows=[];seen=set()
        for subtype,n in quotas.items():
            rng=random.Random(VERSION+':'+family+':'+subtype);made=0;tries=0
            while made<n:
                tries+=1;assert tries<n*100
                r=(probability if family=='probability' else graph)(len(rows),subtype,rng)
                if r is None:continue
                h=r['_meta']['text_sha256']
                if h in seen:continue
                seen.add(h);rows.append(r);made+=1
        path=components/(family+'.candidate.jsonl')
        path.write_text(''.join(dump(r)+'\n' for r in rows))
        coverage[family]={'records':len(rows),'questions':sum(len(r['questions']) for r in rows),'subtypes':dict(Counter(r['_meta']['subtype'] for r in rows)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/'component_status.json').write_text(json.dumps({'status':'incomplete_candidate_components','coverage':coverage,
        'remaining':['Independent visible-text recomputation and semantic review','New insufficient and long-policy components','Retention of unchanged three families and full 1500-context assembly','Fresh validation set and deduplication','Training and evaluation on all seven categories']},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(coverage,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
