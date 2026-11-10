#!/usr/bin/env python3
"""One visible-text-derived step question per weak-family context.

Keeps the 1500 v7 contexts and original questions. Auxiliary questions are
training supervision, never model-visible answers or additional contexts.
"""
import calendar
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction as F
from pathlib import Path
from build_kev_probability_transfer_candidates import read_table, decode
from build_kev_multihop_transfer_candidates import unwrap
from build_kev_insufficient_transfer_candidates import canonical_dates
from build_targeted_v7 import CHECKS, RETAINED
from check_targeted_v4_rules import materialize

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'artifacts/kev_training_eval_20261026'
SOURCE=BASE/'targeted_v7_20261030'
OUT=BASE/'targeted_v8_steps_20261030'
QID='zz_rule_step'

def number(x):
    x=F(x);d=(Decimal(x.numerator)/Decimal(x.denominator)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return format(d,'f')
def pct(x):return number(F(x)*100)+'%'
def cash(x):return ('-' if x<0 else '')+'$'+number(abs(x))
def num_options(value,format_fn=number,extras=()):
    v=F(value);answer=format_fn(v)
    candidates=list(extras)+[0,v+1,v-1,v*2,v/2,v+10]
    if format_fn is pct:
        candidates=[x for x in candidates if 0<=x<=1]+[F(1,4),F(1,2),F(3,4),F(1),max(F(0),v-F(1,20)),min(F(1),v+F(1,20))]
    values=list(dict.fromkeys([answer]+[format_fn(x) for x in candidates if format_fn(x)!=answer]))
    return answer,values[:5]
def get(pattern,s):
    m=re.search(pattern,s);assert m,pattern;return m[1]
def pick_index(r):return int(hashlib.sha256(r['_meta']['id'].encode()).hexdigest()[:12],16)
def month_shift(d,n):
    y,m=divmod(d.year*12+d.month-1+n,12);return date(y,m+1,min(d.day,calendar.monthrange(y,m+1)[1]))

def probability(r,i):
    kind=r['_meta']['subtype'];s=r['state']
    if kind=='table':
        matrix=read_table(s);qid=['forward','reverse'][i%2];instr=r['questions'][qid]['instructions']
        if qid=='forward':
            row,col=re.search(r'Among records from (.+), what percentage have status (.+)\?',instr).groups()
            value=sum(matrix[row].values());prompt=f'For the question conditioned on records from {row}, how many records are in the conditioning set (the denominator before division)?'
        else:
            col,row=re.search(r'Among records with status (.+), what percentage come from (.+)\?',instr).groups()
            value=sum(v[col] for v in matrix.values());prompt=f'For the question conditioned on status {col}, how many records are in the conditioning set (the denominator before division)?'
        extras=[v for counts in matrix.values() for v in counts.values()]+[sum(sum(v.values()) for v in matrix.values())]
        answer,values=num_options(value,lambda x:str(int(x)),extras);return 'probability/conditioning_count',prompt,answer,values
    if isinstance(s,dict):s=s['details']
    s=decode(s,r['_meta']['rate_style'])
    if kind=='bayes':
        rates=[F(v)/100 for v in re.findall(r'([\d.]+)%',s)];assert len(rates)==3
        base,hit,false=rates;signal=base*hit;total=signal+(1-base)*false
        if i%2:value=total;prompt='Before conditioning on a flag, what percentage of the entire population is flagged, including both true and false flags?';tag='flagged_population'
        else:value=signal;prompt='What percentage of the entire population both belongs to the positive class and receives a flag? Use the prevalence and the flag rate within that class.';tag='positive_and_flagged'
        answer,values=num_options(value,pct,[base,hit,false,signal,total,1-total]);return 'probability/'+tag,prompt,answer,values
    if kind in ['all','any','any_fail']:
        ps=[F(v)/100 for v in re.findall(r'([\d.]+)%',s)];assert len(ps)>=2
        if kind=='any':value=(1-ps[0])*(1-ps[1]);prompt='Considering only the first two listed components, what is the probability that both fail?';tag='two_fail'
        else:value=ps[0]*ps[1];prompt='Considering only the first two listed components, what is the probability that both succeed?';tag='two_succeed'
        answer,values=num_options(value,pct,[1-value,ps[0],ps[1],sum(ps[:2])/2]);return 'probability/'+tag,prompt,answer,values
    if kind=='compare':
        p,q,_=[F(v)/100 for v in re.findall(r'([\d.]+)%',s)];value=p*q if 'both A and B happen' in s else 1-(1-p)*(1-q)
        answer,values=num_options(value,pct,[p,q,1-value]);return 'probability/marginal_x','Compute the marginal probability of event X before comparing it with Y.',answer,values
    asked=get(r'cash flow of (\w+)',r['questions']['value']['instructions'])
    projects={}
    for name,cost,terms in re.findall(r'(\w+): upfront cost \$([\d.]+); ([^\n]+)',s):
        outcomes=re.findall(r'(\d+(?:\.\d+)?)%: (gain|lose) \$(\d+\.\d{2})',terms);assert sum(F(p) for p,_,_ in outcomes)==100
        gross=sum(F(p)*F(v)/100*(1 if op=='gain' else -1) for p,op,v in outcomes);projects[name]=(gross,F(cost))
    value,cost=projects[asked];answer,values=num_options(value,cash,[value-cost,value+cost,-value])
    return 'probability/gross_expectation',f'For project {asked}, what is the expected cash flow from the listed outcomes BEFORE subtracting its upfront cost?',answer,values

def policy(r,i):
    s=r['state'];policy_text,claim=s.split('[Claim facts]\n');event=get(r'Event: ([^.]+)\.',claim);item=get(r'Claimed item: ([^.]+)\.',claim)
    blocks=re.findall(r'\[Cover (C\d+)\] ([^\n]+)\n(.*?)(?=\n\n|\Z)',policy_text,re.S)
    selected=[(code,body) for code,title,body in blocks if title==event];assert len(selected)==1;code,body=selected[0]
    cap=F(get(r'Benefit ceiling: \$(\d+\.\d{2})',body));fee=F(get(r'One deductible: \$(\d+\.\d{2})',body));sub=F(get(r'Named-item sublimit: \$(\d+\.\d{2})',body))
    named=get(r'named-item category is ([^;]+);',body);whole=get(r'whole-item category is ([^.]+)\.',body);assert item in [named,whole]
    loss=F(get(r'Approved loss: \$(\d+\.\d{2})',claim));limit=min(cap,sub) if item==named else cap
    before='Subtract one deductible from approved loss' in policy_text
    mode=i%4
    if mode<2:
        value=min(max(F(0),loss-fee),limit) if before else max(F(0),min(loss,limit)-fee)
        prompt='For this calculation only, assume this claim satisfies all purchase, timing and exclusion conditions. Under the cover matching its stated event and item, what amount follows from the approved loss, applicable ceilings and stated deductible order?'
        tag='conditional_payment'
    elif mode==2:
        value=limit;prompt='For the stated claim item, what is the applicable ceiling (the smaller relevant benefit limit or named-item sublimit), before applying any deductible or eligibility decision?';tag='applicable_ceiling'
    else:
        value=max(F(0),loss-fee) if before else min(loss,limit)
        prompt='Assume eligibility for this calculation only. What amount remains immediately after the FIRST operation in the settlement calculation, before performing its second operation? The first operation is the deductible or cap, as specified by the policy.';tag='first_operation'
    answer,values=num_options(value,cash,[0,loss,cap,sub,fee,loss-fee,min(loss,limit),value+fee])
    assert '$0.00' in values and value>0
    return 'policy/'+tag,prompt,answer,values

def multihop(r,i):
    s=unwrap(r['state']);kind=r['_meta']['subtype']
    if kind=='dependency_candidates':
        edges=[]
        for line in s.splitlines()[2:-1]:
            m=re.fullmatch(r'(\w+) requires (\w+) through a (hard|soft) dependency\.',line)
            if m:edges.append((m[1],m[2],m[3]));continue
            m=re.fullmatch(r'(\w+) is a (hard|soft) prerequisite for (\w+)\.',line)
            if m:edges.append((m[3],m[1],m[2]));continue
            m=re.fullmatch(r'Dependency: consumer=(\w+); prerequisite=(\w+); kind=(hard|soft)\.',line);assert m;edges.append(m.groups())
        failed=get(r'Initial failed unit: (\w+)',s);new={a for a,b,t in edges if b==failed and t=='hard'}
        label=lambda ns:', '.join(sorted(ns)) if ns else 'No additional unit'
        nodes=sorted({a for a,b,t in edges}|{b for a,b,t in edges});answer=label(new)
        options=[answer,label({b for a,b,t in edges if a==failed}),label({a for a,b,t in edges if b==failed}),label(set()),label({failed})]+[label({n}) for n in nodes]
        return 'multihop/first_failure_round','Immediately after ONE propagation round, which set of additional units fails because its hard prerequisite was initially down? Exclude the initially failed unit and do not propagate a second time.',answer,options
    if kind in ['rank_escalation','exact_supervisor_hops']:
        links=dict(re.findall(r'(\w+) has supervisor (\w+)\.',s));start=get(r'Request origin: (\w+)',s) if kind=='rank_escalation' else get(r'start at (\w+) and follow exactly',s)
        return 'multihop/first_supervisor',f'Who is the immediate supervisor of {start}, before following any further supervisor links or applying rank requirements?',links[start],list(links)+list(links.values())
    if kind=='dated_roster':
        routes=dict(re.findall(r'The owner of (\w+) is team (\w+)\.',s));asset=get(r'Asset needing help: (\w+)',s);team=routes[asset]
        role=['primary contact','backup contact','duty lead'][i%3];person=dict(re.findall(r'(\w+) '+role+r': (\w+)\.',s))[team]
        leave={p:(date.fromisoformat(a),date.fromisoformat(b)) for p,a,b in re.findall(r'Absence for (\w+): ([\d-]+) to ([\d-]+), inclusive\.',s)}
        day=date.fromisoformat(get(r'Date needing coverage: ([\d-]+)',s));available=person not in leave or not leave[person][0]<=day<=leave[person][1]
        return 'multihop/contact_availability',f'On the incident date, is {person} available according to the stated absence records?', 'Available' if available else 'Unavailable',['Available','Unavailable']
    shares=[(owner,F(p),child) for owner,p,child in re.findall(r'(\w+) owns ([\d.]+)% of (\w+)\.',s)];owner,percent,child=shares[i%len(shares)]
    return 'multihop/direct_majority',f'Considering ONLY the directly stated voting stake, does {owner} own strictly more than half of {child}? Ignore all indirect stakes for this question.','Yes' if percent>50 else 'No',['Yes','No']

def insufficient(r,i):
    s=canonical_dates(unwrap(r['state']));scene=get(r'CASE TYPE: (\w+)',s)
    integer=lambda p:int(get(p,s));dt=lambda p:date.fromisoformat(get(p,s))
    optional=lambda p:re.search(p,s)
    if scene=='approval':
        low=integer(r'Amounts below \$(\d+)');high=integer(r'through \$(\d+), approval');amount=integer(r'payment is \$(\d+)')
        ans='No approval is required' if amount<low else 'Team Manager' if amount<=high else 'Department Director'
        return 'insufficient/required_rank','For the payment amount alone, what minimum approval is required? This asks the requirement, not whether the actual signatory meets it.',ans,['No approval is required','Assistant','Specialist','Team Manager','Senior Manager','Department Director','Executive Director']
    if scene in ['tenure','warranty']:
        if scene=='tenure':
            years=integer(r'after (\d+) complete calendar years?');known=optional(r'employment began on ([\d-]+)');start=date.fromisoformat(known[1]) if known else dt(r'move took place on ([\d-]+)');end=month_shift(start,12*years)
            prompt='Using the latest company hire date consistent with the stated facts, on what date does the required employment anniversary occur?'
        else:
            months=integer(r'lasts (\d+) calendar months');start=dt(r'purchase date is ([\d-]+)');end=month_shift(start,months);prompt='On what date does the warranty expire under the calendar-month rule, independently of the cause of the damage?'
        answer=str(end);values=[answer,str(end-timedelta(days=1)),str(end+timedelta(days=1)),str(month_shift(end,-1)),str(month_shift(end,1))]
        return 'insufficient/'+('latest_anniversary' if scene=='tenure' else 'warranty_expiry'),prompt,answer,values
    if scene=='price_match':
        ours=integer(r'Our listed price is \$(\d+)');gap=integer(r'at most (\d+)%');v=F(ours*gap,100);answer,values=num_options(v,cash,[ours,ours-v,gap])
        return 'insufficient/maximum_reduction','What is the largest dollar reduction from our listed price allowed by the percentage limit, regardless of stock availability?',answer,values
    if scene=='return':
        request=dt(r'requested on ([\d-]+)');order=dt(r'placed on ([\d-]+)');known=optional(r'Delivery took place on ([\d-]+)')
        lo=hi=(request-date.fromisoformat(known[1])).days if known else 0
        if not known:hi=(request-order).days
        unit='calendar days';prompt='What is the tightest possible range of elapsed calendar days from delivery to the return request, using all stated date constraints?'
    elif scene=='shipping':
        subtotal=integer(r'before discount is \$(\d+)');maximum=integer(r'from \$0 through \$(\d+)');known=optional(r'merchandise discount is \$(\d+)')
        lo=subtotal-(int(known[1]) if known else maximum);hi=subtotal-(int(known[1]) if known else 0)
        unit='dollars';prompt='What is the tightest possible range of merchandise value after discount, excluding taxes and shipping, given the stated facts?'
    else:
        assert scene=='overtime';total=sum(integer(d+r': (\d+) hours?') for d in ['Monday','Tuesday','Wednesday','Thursday']);known=optional(r'Friday: (\d+) hours?');maximum=integer(r'between 0 and (\d+)')
        lo=total+(int(known[1]) if known else 0);hi=total+(int(known[1]) if known else maximum)
        unit='hours';prompt='What is the tightest possible range of total weekly hours using the known weekday hours and the permitted range for any missing Friday hours?'
    fmt=lambda a,b:f'{a} to {b} {unit}, inclusive'
    answer=fmt(lo,hi);values=[answer,fmt(0,hi+1),fmt(lo+1,hi+1),fmt(max(0,lo-1),max(0,hi-1)),fmt(lo,hi+10),'No finite range follows from the facts']
    return 'insufficient/'+scene+'_range',prompt,answer,values

FUNCTIONS={'probability':probability,'policy':policy,'multihop':multihop,'insufficient':insufficient}

def spec(r):return FUNCTIONS[r['_meta']['family']](r,pick_index(r))

def auxiliary(r):
    tag,prompt,answer,values=spec(r);values=list(dict.fromkeys([answer]+values));assert len(values)>=2
    # At most five options, without dropping the correct answer.
    wrong=[v for v in values if v!=answer][:4];values=[answer]+wrong
    random.Random('v8-step/'+r['_meta']['id']).shuffle(values);criteria={chr(97+j):v for j,v in enumerate(values)}
    label=next(k for k,v in criteria.items() if v==answer)
    return tag,{'type':'choice','instructions':prompt,'criteria':criteria,'label':label,'target':{label:1.0},'src':'targeted-v8-steps/'+r['_meta']['family']}

def verify_step(r):
    clean=copy.deepcopy(r);clean['_meta'].pop('facts',None);tag,prompt,answer,_=spec(clean)
    q=r['questions'][QID];assert q['instructions']==prompt and q['criteria'][q['label']]==answer
    assert q['target']=={q['label']:1.0};return tag

def main():
    assert not (OUT/'launch.json').exists(),'Never rebuild an active run'
    OUT.mkdir(exist_ok=True);counts=Counter();wrong_labels=0
    original_lines=(SOURCE/'train.jsonl').read_text().splitlines();originals=[json.loads(l) for l in original_lines];rows=[];lines=[]
    for old_line,original in zip(original_lines,originals):
        r=copy.deepcopy(original);family=r['_meta']['family']
        if family in RETAINED:lines.append(old_line);rows.append(r);continue
        CHECKS[family](r);tag,q=auxiliary(r);r['questions'][QID]=q;r['_meta']['step_supervision']=tag
        assert r['state']==original['state'] and {k:v for k,v in r['questions'].items() if k!=QID}==original['questions']
        verify_step(r);materialize(r);counts[tag]+=1
        for label in q['criteria']:
            if label==q['label']:continue
            bad=copy.deepcopy(r);bad['questions'][QID]['label']=label;bad['questions'][QID]['target']={label:1.0}
            try:verify_step(bad)
            except AssertionError:wrong_labels+=1
            else:raise AssertionError('Wrong step answer accepted')
        rows.append(r);lines.append(json.dumps(r,ensure_ascii=False,sort_keys=True))
    assert len(rows)==1500 and sum(counts.values())==1200
    path=OUT/'train.jsonl';path.write_text('\n'.join(lines)+'\n')
    for r in map(json.loads,path.read_text().splitlines()):
        if r['_meta']['family'] not in RETAINED:verify_step(r)
    for name in ['development.jsonl','train_probe.jsonl','evaluate_development.py']:(OUT/name).write_bytes((SOURCE/name).read_bytes())
    devsteps=[]
    for r in map(json.loads,(SOURCE/'development.jsonl').read_text().splitlines()):
        if r['_meta']['family'] not in RETAINED:
            tag,q=auxiliary(r);r['questions'][QID]=q;r['_meta']['step_supervision']=tag;verify_step(r);materialize(r)
        devsteps.append(r)
    dp=OUT/'development_steps.jsonl';dp.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in devsteps))
    manifest={'status':'assembled_not_launched','goal_achieved':False,'contexts':1500,'replay_separate':6000,'original_questions':2320,'auxiliary_questions':1200,'total_questions':sum(len(r['questions']) for r in rows),
        'family_contexts':dict(Counter(r['_meta']['family'] for r in rows)),'step_types':dict(counts),'wrong_label_mutations_rejected':wrong_labels,
        'train_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_train_sha256':hashlib.sha256((SOURCE/'train.jsonl').read_bytes()).hexdigest(),
        'development_steps':{'contexts':len(devsteps),'questions':sum(len(r['questions']) for r in devsteps),'sha256':hashlib.sha256(dp.read_bytes()).hexdigest()},
        'checks':{'all_states_and_original_questions_unchanged':True,'retained_three_families_byte_identical':True,'same_ids_and_record_order':True,'step_answers_recomputed_without_metadata_facts':True},
        'training_plan':{'init':'original pre-targeted stage3','lr':1e-5,'epochs':1,'seed':101,'replay':6000},
        'limitations':['This changes supervision, not the number of independent contexts.','Same-author visible-text rechecking is not independent external review.',
          'Step gold answers are labels only; branches do not see each other or each other\'s gold answers. There is no explicit consistency loss.',
          'Mean per-question loss makes original questions retain between half and three-quarters of each changed record\'s unaugmented CE share; augmentation must be audited before launch.',
          'Additional question RNG draws can change none-pair augmentation; original augmentation code remains unchanged.','No effect measured; official diagnostic tests have already informed design.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    examples=[next(r for r in rows if r['_meta'].get('step_supervision')==tag) for tag in counts]
    (OUT/'step_examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
