#!/usr/bin/env python3
"""Read rendered probability/graph questions and recompute their answers."""
import json,re
from fractions import Fraction as F
from check_targeted_v4_rules import OUT,gold,find,materialize

def pct(v):return f'{float(100*v):.2f}%'
def cash(v):return ('-' if v<0 else '')+f'${abs(float(v)):.2f}'

def probability(r):
    s=r['state'];kind=r['_meta']['subtype'];answers={}
    if kind=='table':
        if '| Origin |' in s:
            rows=re.findall(r'\| [^|\n]+ \| (\d+) \| (\d+) \|',s)
            a,b,c,d=[int(v) for pair in rows for v in pair]
        else:
            vals=re.findall(r'(\d+) (?:items classified as|as)',s)
            # The first group's second count follows "and N as".
            a,b,c,d=map(int,vals)
        answers={'forward':pct(F(a,a+b)),'reverse':pct(F(a,a+c))}
    elif kind=='bayes':
        base,hit,false=map(int,re.findall(r'(\d+)%',s));p=F(base*hit,base*hit+(100-base)*false)
        answers={'posterior':pct(p)}
        assert r['questions']['more_likely']['label']==(p>F(1,2))
        q=r['questions']['bucket'];matches=[]
        for i,b in enumerate(q['criteria']):
            l,u=map(int,re.findall(r'(\d+)%',b))
            if l<=100*p<u or u==100 and p==1:matches.append(i)
        assert matches==[q['label']]
    elif kind in ('all','any','any_fail'):
        ps=[F(p)/100 for p in re.findall(r'(\d+)%',s)];allp=F(1);none=F(1)
        for p in ps:allp*=p;none*=1-p
        answers={'probability':pct({'all':allp,'any':1-none,'any_fail':1-allp}[kind])}
    elif kind=='compare':
        p,q,other=[F(p)/100 for p in re.findall(r'([\d.]+)%',s)]
        first=p*q if 'both A and B happen' in s else p+q-p*q
        answers={'decision':'X is more likely' if first>other else 'Y is more likely' if first<other else 'They have equal probabilities'}
    else:
        values={}
        for name,cost,rest in re.findall(r'(\w+): upfront cost \$([\d.]+); ([^\n]+)',s):
            terms=re.findall(r'(\d+)%: (gain|lose) \$([\d]+\.\d{2})',rest)
            assert sum(int(p) for p,_,_ in terms)==100
            values[name]=sum(F(p)*F(v)/100*(1 if op=='gain' else -1) for p,op,v in terms)-F(cost)
        winner=max(values,key=values.get);assert list(values.values()).count(values[winner])==1
        asked=find(r'cash flow of (\w+)',r['questions']['value']['instructions'])
        answers={'project':winner,'value':cash(values[asked])}
    for q,value in answers.items():assert gold(r,q)==value,(r['_meta']['id'],q,gold(r,q),value)

def graph(r):
    s=r['state'];kind=r['_meta']['subtype']
    if kind=='dependency':
        edges=re.findall(r'(\w+) depends on (\w+)\.',s)
        failed=find(r'Initially only (\w+) is unavailable',s);affected={failed}
        while True:
            grown=affected|{a for a,b in edges if b in affected}
            if grown==affected:break
            affected=grown
        answer=', '.join(sorted(affected))
    elif kind=='escalation':
        links=dict(re.findall(r'(\w+) escalates to (\w+)\.',s))
        attrs={n:(a=='available' and b=='authorized') for n,a,b in re.findall(r'(\w+): (available|unavailable); (authorized|not authorized)\.',s)}
        node=find(r'A case starts at (\w+)',s);seen=set()
        while node in links:
            node=links[node];assert node not in seen;seen.add(node)
            if attrs[node]:break
        else:raise AssertionError('no eligible successor')
        answer=node
    else:
        parents={child:owner for owner,p,child in re.findall(r'(\w+) owns (\d+)% of (\w+)\.',s) if int(p)>50}
        node=find(r'controller of (\w+)',r['questions']['decision']['instructions']);seen=set()
        while node in parents:
            node=parents[node];assert node not in seen;seen.add(node)
        answer=node
    assert gold(r,'decision')==answer

def main():
    counts={}
    for family,check in [('probability',probability),('multihop',graph)]:
        rows=[json.loads(l) for l in (OUT/'components'/f'{family}.candidate.jsonl').read_text().splitlines()]
        for r in rows:materialize(r);check(r)
        counts[family]=len(rows)
    (OUT/'numeric_validation.json').write_text(json.dumps({'visible_text_recomputed':counts,'independent_external_reviewer':False},indent=2)+'\n')
    print(counts)

if __name__=='__main__':main()
