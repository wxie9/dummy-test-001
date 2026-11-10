#!/usr/bin/env python3
"""Fresh 280-context component with operational actions and richer rules."""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date, datetime, timedelta
from build_targeted_v4_components import ROOT, record, choice
from build_targeted_v5 import digest
from build_kev_multihop_transfer_candidates import wrap, unwrap
from check_targeted_v4_rules import gold, materialize

BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'insufficient_transfer_candidates_20261030'
VERSION='insufficient-transfer-20261030'
SCENARIOS=['return','approval','tenure','shipping','overtime','warranty','price_match']
UNKNOWN='The stated facts permit different decisions; more information is needed.'
ACTIONS={
 'return':['Accept the return request','Reject the return request'],
 'approval':['Authorize the payment','Obtain a qualifying approval before payment'],
 'tenure':['Grant the employment benefit','Decline the employment benefit'],
 'shipping':['Provide free shipping','Charge the shipping fee'],
 'overtime':['Pay overtime for this week','No overtime payment is due'],
 'warranty':['Repair under the warranty','Decline warranty coverage'],
 'price_match':['Match the competitor price','Decline the requested price match','Keep our existing price; it is already no higher']}
RANKS=['Assistant','Specialist','Team Manager','Senior Manager','Department Director','Executive Director']

def months_shift(d,n):
    year,month=divmod(d.year*12+d.month-1+n,12)
    return date(year,month+1,d.day)

def split_hours(total,maximum,rng):
    assert 0<=total<=4*maximum
    values=[]
    for remaining in [3,2,1,0]:
        v=rng.randint(max(0,total-remaining*maximum),min(maximum,total));values.append(v);total-=v
    return values

def make(scene,i,variant,rng):
    known=variant in ['yes','no'];positive=variant=='yes';non=variant=='nondeciding'
    today=date(2031,rng.randint(1,12),rng.randint(6,22));facts=[]
    if scene=='return':
        window=rng.choice([10,20,28,35,60]);span=rng.randint(1,window) if non else window+rng.randint(1,25)
        elapsed=rng.randint(0,window) if positive else window+rng.randint(1,span-window) if not non else 0
        policy=f'A return is accepted when the elapsed calendar days from delivery to request are at most {window}, including the boundary. Delivery occurred between ordering and requesting, inclusive. There are no other eligibility requirements.'
        facts=[f'The order was placed on {today-timedelta(days=span)}.',f'The return was requested on {today}.']
        if known:facts.append(f'Delivery took place on {today-timedelta(days=elapsed)}.')
        elif i%2:facts.append('The delivery date is absent from this file.')
    elif scene=='approval':
        low=rng.choice([100,400,750]);high=rng.choice([2000,6000,18000]);band=i%2
        amount=rng.randint(1,low-1) if non else rng.randint(low,high) if band==0 else rng.randint(high+1,high*2)
        need=2 if amount<=high else 4;level=rng.randint(need,5) if positive else rng.randrange(need)
        policy=f'Amounts below ${low} need no approval. For amounts from ${low} through ${high}, approval must come from a Team Manager or higher. Above ${high}, approval must come from a Department Director or higher. Rank order from lowest to highest: '+', '.join(RANKS)+'. Only the actual signatory supplies approval; a reviewer or copied colleague does not.'
        signatory=rng.choice(['Elin','Tomas','Nadia','Felix','Pavel','Mira'])
        facts=[f'The requested payment is ${amount}.',f'The actual signatory is {signatory}.','The copied colleague is an Executive Director.']
        if known:facts.append(f'The actual signatory holds the rank {RANKS[level]}.')
        elif i%2:facts.append('The signatory rank has not been supplied.')
    elif scene=='tenure':
        years=rng.choice([1,2,4,6]);required=years*12
        move_age=required+rng.randint(1,18) if non else rng.randint(1,required-1)
        tenure=required+rng.randint(0,24) if positive else rng.randint(move_age,required-1) if not non else move_age
        policy=f'The benefit is granted after {years} complete calendar '+('year' if years==1 else 'years')+' of continuous company employment. Eligibility starts on the corresponding hire-date anniversary. A team move does not restart employment; the company hire date is on or before the team move. Employment has been continuous.'
        facts=[f'The benefit application date is {today}.',f'The team move took place on {months_shift(today,-move_age)}.']
        if known:
            jitter=rng.randint(-5,0 if tenure in [required,move_age] else 5)
            hire=months_shift(today,-tenure)+timedelta(days=jitter)
            assert hire<=months_shift(today,-move_age)
            facts.append(f'The company employment began on {hire}.')
        elif i%2:facts.append('The original company hire date is unavailable.')
    elif scene=='shipping':
        threshold=rng.choice([60,90,130,180]);cap=rng.choice([20,40,80]);subtotal=threshold+cap//2
        if non:subtotal=threshold-1-rng.randrange(10) if i%2 else threshold+cap+rng.randrange(10)
        discount=rng.randint(0,cap//2) if positive else rng.randint(cap//2+1,cap)
        policy=f'Free shipping applies when merchandise value after its discount is at least ${threshold}. Otherwise charge shipping. The discount can be any whole-dollar amount from $0 through ${cap}. Taxes and shipping charges do not enter the threshold calculation.'
        facts=[f'The merchandise value before discount is ${subtotal}.',f'The tax charge is ${rng.randint(2,18)}.']
        if known:facts.append(f'The merchandise discount is ${discount}.')
        elif i%2:facts.append('The discount amount is not stated.')
    elif scene=='overtime':
        maximum=12;threshold=rng.choice([36,40,44]);total=threshold-rng.randint(1,maximum-1)
        if non:total=threshold+1 if i%2 else threshold-maximum
        friday=rng.randint(threshold-total+1,maximum) if positive else rng.randint(0,threshold-total) if not non else 0
        hours=split_hours(total,maximum,rng)
        policy=f'Weekly hours strictly above {threshold} earn overtime. There is one shift per weekday, each between 0 and {maximum} whole hours inclusive, and no weekend work.'
        facts=[f'{day}: {hour} '+('hour.' if hour==1 else 'hours.') for day,hour in zip(['Monday','Tuesday','Wednesday','Thursday'],hours)]
        if known:facts.append(f'Friday: {friday} '+('hour.' if friday==1 else 'hours.'))
        elif i%2:facts.append('The Friday hours are not recorded.')
    elif scene=='warranty':
        duration=rng.choice([6,12,18,30]);age=duration+rng.randint(0,6) if non else rng.randint(0,duration-1)
        purchase=months_shift(today,-age);cause='production defect' if positive else 'accidental damage'
        policy=f'The warranty lasts {duration} calendar months from purchase and ends at the beginning of the corresponding monthly anniversary. Before that expiry, only production defects qualify. Accidental damage is excluded. These are the only two possible causes; after expiry neither qualifies.'
        facts=[f'The purchase date is {purchase}.',f'The claim date is {today}.']
        if known:facts.append(f'The confirmed cause is {cause}.')
        elif i%2:facts.append('The failure cause has not been determined.')
    else:
        ours=rng.choice([200,400,600,1000]);gap=rng.choice([5,10,20,25]);theirs=ours-(ours*gap//100)//2
        if non:theirs=ours+rng.randint(0,20) if i%2 else ours-ours*gap//100-1
        policy=f'Match an identical in-stock competitor item only when its price is below ours and its reduction is at most {gap}% of our price. First, if its price is at least ours, retain our existing price without an adjustment regardless of stock. Otherwise, if the reduction exceeds the limit or the item is out of stock, decline the match. Item identity is already verified.'
        facts=[f'Our listed price is ${ours}.',f'The competitor listed price is ${theirs}.']
        if known:facts.append('The competitor item is '+('in stock.' if positive else 'out of stock.'))
        elif i%2:facts.append('Competitor stock availability is unreported.')
    rng.shuffle(facts)
    s=f'CASE TYPE: {scene}\nGOVERNING RULE\n{policy}\nAVAILABLE FACTS\n'+'\n'.join(facts)
    # Construct the intended label separately from the visible-text solver.
    if variant=='yes':expected={ACTIONS[scene][0]}
    elif variant=='no':expected={ACTIONS[scene][1]}
    elif variant=='unknown':expected=set(ACTIONS[scene][:2])
    else:
        positive_nondeciding=scene in ['return','approval','tenure'] or (scene=='shipping' and i%2==0) or (scene=='overtime' and i%2==1)
        expected={ACTIONS[scene][0 if positive_nondeciding else 1]}
        if scene=='price_match' and i%2:expected={ACTIONS[scene][2]}
    outcomes=solve(s);assert outcomes==expected,(scene,variant,outcomes,expected)
    answer=next(iter(expected)) if len(expected)==1 else UNKNOWN
    if variant=='yes':assert answer==ACTIONS[scene][0]
    if variant=='no':assert answer==ACTIONS[scene][1]
    if variant=='unknown':assert len(outcomes)>1
    if non:assert len(outcomes)==1
    if (i//3)%2:
        presented=re.sub(r'\b\d{4}-\d{2}-\d{2}\b',lambda m:date.fromisoformat(m[0]).strftime('%B %d, %Y'),s)
        assert canonical_dates(presented)==s
        s=presented
    q=choice(rng,'Which action follows from the rule and all stated facts?',answer,ACTIONS[scene]+[UNKNOWN])
    return record('insufficient',i,wrap(s,i),{'decision':q},{'scenario':scene,'variant':variant,'possible_outcomes':sorted(outcomes)},scene+'__'+variant,'遍历可行的缺失字段补全；只有所有补全结论相同才可确定动作。')

def canonical_dates(s):
    return re.sub(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{2}, \d{4}\b',lambda m:datetime.strptime(m[0],'%B %d, %Y').date().isoformat(),s)

def solve(s):
    s=canonical_dates(s)
    def take(pattern):
        m=re.search(pattern,s);assert m,pattern
        return m[1]
    def integer(pattern):return int(take(pattern))
    def dt(pattern):return date.fromisoformat(take(pattern))
    def optional(pattern):
        m=re.search(pattern,s);return m[1] if m else None
    scene=take(r'CASE TYPE: (\w+)');yes,no=ACTIONS[scene][:2]
    if scene=='return':
        limit=integer(r'at most (\d+),');request=dt(r'requested on ([\d-]+)');order=dt(r'placed on ([\d-]+)');delivery=optional(r'Delivery took place on ([\d-]+)')
        days=[(request-date.fromisoformat(delivery)).days] if delivery else range((request-order).days+1)
        return {yes if d<=limit else no for d in days}
    if scene=='approval':
        low=integer(r'Amounts below \$(\d+)');high=integer(r'through \$(\d+), approval');amount=integer(r'payment is \$(\d+)')
        ranks=take(r'lowest to highest: ([^.]+)').split(', ');rank=optional(r'actual signatory holds the rank ([^.]+)')
        levels=[ranks.index(rank)] if rank else range(len(ranks));need=ranks.index('Team Manager' if amount<=high else 'Department Director')
        return {yes if amount<low or level>=need else no for level in levels}
    if scene=='tenure':
        years=integer(r'after (\d+) complete calendar years?');apply=dt(r'application date is ([\d-]+)');move=dt(r'move took place on ([\d-]+)');hire=optional(r'employment began on ([\d-]+)')
        # The latest feasible hire date and a sufficiently early witness bracket all dates.
        dates=[date.fromisoformat(hire)] if hire else [move,date(apply.year-years-1,apply.month,apply.day)]
        return {yes if (apply.year-h.year-( (apply.month,apply.day)<(h.month,h.day)))>=years else no for h in dates}
    if scene=='shipping':
        threshold=integer(r'at least \$(\d+)');maximum=integer(r'from \$0 through \$(\d+)');subtotal=integer(r'before discount is \$(\d+)');discount=optional(r'merchandise discount is \$(\d+)')
        values=[int(discount)] if discount else range(maximum+1)
        return {yes if subtotal-d>=threshold else no for d in values}
    if scene=='overtime':
        threshold=integer(r'strictly above (\d+)');maximum=integer(r'between 0 and (\d+)');hours=[integer(day+r': (\d+) hours?') for day in ['Monday','Tuesday','Wednesday','Thursday']];fri=optional(r'Friday: (\d+) hours?')
        values=[int(fri)] if fri else range(maximum+1)
        return {yes if sum(hours)+v>threshold else no for v in values}
    if scene=='warranty':
        duration=integer(r'lasts (\d+) calendar months');purchase=dt(r'purchase date is ([\d-]+)');claim=dt(r'claim date is ([\d-]+)');cause=optional(r'confirmed cause is ([^.]+)')
        age=(claim.year-purchase.year)*12+claim.month-purchase.month-(claim.day<purchase.day)
        return {yes if age<duration and c=='production defect' else no for c in ([cause] if cause else ['production defect','accidental damage'])}
    ours=integer(r'Our listed price is \$(\d+)');theirs=integer(r'competitor listed price is \$(\d+)');gap=integer(r'at most (\d+)%');stock=optional(r'competitor item is (in stock|out of stock)')
    if theirs>=ours:return {ACTIONS[scene][2]}
    return {yes if (ours-theirs)*100<=ours*gap and v=='in stock' else no for v in ([stock] if stock else ['in stock','out of stock'])}

def verify(r):
    outcomes=solve(unwrap(r['state']));expected=next(iter(outcomes)) if len(outcomes)==1 else UNKNOWN
    assert gold(r,'decision')==expected
    materialize(r)

def main():
    OUT.mkdir(exist_ok=True);seen=set()
    paths=list((ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'))+[BASE/'targeted_v6_20261030/train.jsonl',BASE/'targeted_v6_20261030/development.jsonl']
    for p in paths:seen.update(digest(json.loads(l)['state']) for l in p.read_text().splitlines())
    manifest={'status':'component_only_not_trained','planned_train_contexts':280,'files':{},'limitations':['Single operational action question per context, unlike v6 five views; supervision density changes.','Same-author checker; no independent semantic review.','Official tests informed diagnosis; not blind generalization.']}
    for split,counts in [('train',{'yes':12,'no':12,'unknown':12,'nondeciding':4}),('development',{'yes':3,'no':3,'unknown':3,'nondeciding':1})]:
        rows=[];rejected=0;variants=Counter();answers=Counter()
        for scene in SCENARIOS:
            for variant,n in counts.items():
                for i in range(n):
                    for attempt in range(10000):
                        r=make(scene,i,variant,random.Random(f'{VERSION}/{split}/{scene}/{variant}/{i}/{attempt}'))
                        h=digest(r['state']);raw=digest(unwrap(r['state']))
                        if h not in seen and raw not in seen:break
                    else:raise AssertionError('No unique draw')
                    seen.update([h,raw]);m=r['_meta'];m.update(id=f'{VERSION}/{split}/{scene}/{variant}/{i}',group_id=f'{VERSION}/{split}/{scene}/{variant}/{i}',source=VERSION,split=split,text_sha256=h)
                    for q in r['questions'].values():q['src']=VERSION
                    verify(r);q=r['questions']['decision']
                    for k in q['criteria']:
                        if k==q['label']:continue
                        bad=copy.deepcopy(r);bad['questions']['decision']['label']=k
                        try:verify(bad)
                        except AssertionError:rejected+=1
                        else:raise AssertionError('Incorrect label passed')
                    variants[scene+'/'+variant]+=1;answers[gold(r,'decision')]+=1;rows.append(r)
        random.Random(VERSION+split).shuffle(rows);p=OUT/(split+'.candidate.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
        for line in p.read_text().splitlines():verify(json.loads(line))
        manifest['files'][split]={'contexts':len(rows),'questions':len(rows),'variants':dict(variants),'answers':dict(answers),'incorrect_labels_rejected':rejected,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        (OUT/(split+'.examples.json')).write_text(json.dumps([next(r for r in rows if r['_meta']['facts']['scenario']==s and r['_meta']['facts']['variant']==v) for s in SCENARIOS for v in counts],ensure_ascii=False,indent=2)+'\n')
    manifest['checks']={'visible_label_recomputation':True,'serialized_roundtrip_verified':True,'normalized_state_train_dev_prior_v6_and_frozen_test_overlap':0}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({s:{k:v for k,v in f.items() if k not in ['variants','answers']} for s,f in manifest['files'].items()},indent=2))

if __name__=='__main__':main()
