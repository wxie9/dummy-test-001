#!/usr/bin/env python3
"""Authored missing-information and multi-benefit contract generators."""
import random
from datetime import date, timedelta
from collections import Counter
from build_targeted_v4_components import OUT, VERSION, record, choice, dump, cash

ANS={True:'The requirement is satisfied',False:'The requirement is not satisfied',None:'Cannot determine from the information given'}

def insufficient(index,scenario,variant,rng):
    missing=variant in ('unknown','nondeciding')
    non=variant=='nondeciding'
    wanted=variant=='yes'
    today=date(2028,rng.randint(1,12),rng.randint(1,25))
    name=rng.choice(['Ari','Mina','Leon','Sana','Bo','Nora'])
    if scenario=='return':
        limit=rng.choice([14,21,30,45]);window=limit+rng.randint(8,25)
        if non:window=rng.randint(2,limit-1)
        elapsed=rng.randint(0,limit) if wanted else limit+rng.randint(1,7)
        order=today-timedelta(days=window)
        policy=f'Returns qualify if requested no more than {limit} elapsed calendar days after delivery, inclusive. Every order below was delivered between its order date and its return request, inclusive. There are no other requirements.'
        case=f'Order date: {order}. Return requested: {today}.'
        if not missing:case+=f' Delivered: {today-timedelta(days=elapsed)}.'
        values=[0,window] if missing else [elapsed];decisions=[v<=limit for v in values]
        witness=[{'delivery_elapsed_days':v,'eligible':v<=limit} for v in values]
        question='Does this return qualify?'
    elif scenario=='approval':
        limit=rng.choice([150,200,300,500]);amount=rng.randint(limit+100,limit+3000) if not non else rng.randint(10,limit-1)
        level=2 if wanted else 1
        policy=f'Payments below ${limit} require no approval. All other payments require an actual approver with authority level at least 2. Every approver has level 1, 2 or 3. A copied colleague is not an approver. Decide only whether authorization is sufficient.'
        case=f'Amount: ${amount}. Actual approver: {name}. Copied colleague: Director Tessa, authority level 3.'
        if not missing:case+=f' {name} has authority level {level}.'
        values=[1,3] if missing else [level];decisions=[amount<limit or v>=2 for v in values]
        witness=[{'actual_approver_level':v,'eligible':d} for v,d in zip(values,decisions)];question='Is the payment sufficiently authorized?'
    elif scenario=='tenure':
        limit=rng.choice([365,540,730,1095]);minimum=rng.randint(30,limit-20) if not non else limit+rng.randint(1,100)
        elapsed=limit+rng.randint(1,100) if wanted or non else rng.randint(minimum,limit-1)
        transfer=today-timedelta(days=minimum)
        policy=f'The benefit requires at least {limit} elapsed days of continuous employment by {today}. Team transfers do not reset employment. The employee joined the company on or before the stated transfer date and has remained continuously employed through the application date.'
        case=f'{name} transferred to the Support team on {transfer}.'
        if not missing:case+=f' Company hire date: {today-timedelta(days=elapsed)}.'
        values=[minimum,limit+300] if missing else [elapsed];decisions=[v>=limit for v in values]
        witness=[{'company_tenure_days':v,'eligible':v>=limit} for v in values];question='Is the employee eligible for the benefit?'
    elif scenario=='shipping':
        limit=rng.choice([80,100,120,150]);cap=rng.choice([30,40,60]);subtotal=limit+cap//2 if not non else limit-rng.randint(5,20)
        discount=rng.randint(0,cap//2) if wanted else rng.randint(cap//2+1,cap)
        policy=f'Shipping is free if merchandise subtotal minus discount is at least ${limit}. The merchandise discount is between $0 and ${cap} inclusive. Ignore taxes and delivery fees in this calculation.'
        case=f'Merchandise subtotal: ${subtotal}. Tax: ${rng.randint(2,15)}.'
        if not missing:case+=f' Merchandise discount: ${discount}.'
        values=[0,cap] if missing else [discount];decisions=[subtotal-v>=limit for v in values]
        witness=[{'discount':v,'eligible':d} for v,d in zip(values,decisions)];question='Does this order receive free shipping?'
    elif scenario=='overtime':
        limit=rng.choice([35,38,40]);maxshift=10
        total=limit-5 if not non else limit-11
        first=[total//4]*3+[total-3*(total//4)]
        last=rng.randint(6,10) if wanted else rng.randint(0,5)
        policy=f'Overtime applies when total hours strictly exceed {limit} in a Monday-to-Friday week. There is at most one shift per day, each between 0 and {maxshift} hours inclusive. No weekend work occurs.'
        case=f'Monday through Thursday hours: {first}. Payroll desk: {rng.choice(["East","West","Central"])}.'
        if not missing:case+=f' Friday hours: {last}.'
        values=[0,maxshift] if missing else [last];decisions=[total+v>limit for v in values]
        witness=[{'friday_hours':v,'eligible':d} for v,d in zip(values,decisions)];question='Does overtime apply to this week?'
    elif scenario=='warranty':
        expiry=today+timedelta(days=rng.randint(10,300)) if not non else today-timedelta(days=rng.randint(1,90))
        cause='manufacturing defect' if wanted else 'accidental damage'
        policy=f'This warranty expires on {expiry}, inclusive. A claim by that date qualifies only for a manufacturing defect; accidental damage never qualifies. Every claim has exactly one of these causes. Claims after expiry do not qualify regardless of cause.'
        case=f'Claim received: {today}. Item serial: W{rng.randint(10000,99999)}.'
        if not missing:case+=f' Technician confirmed cause: {cause}.'
        values=['manufacturing defect','accidental damage'] if missing else [cause]
        decisions=[today<=expiry and v=='manufacturing defect' for v in values]
        witness=[{'cause':v,'eligible':d} for v,d in zip(values,decisions)];question='Is the claim covered?'
    else:
        price=rng.choice([200,300,400,500]);limit=rng.choice([10,15,20]);reduction=limit-5 if not non else limit+5
        competitor=price*(100-reduction)//100;stock=wanted
        policy=f'A price match qualifies if the identical item is in stock at the competitor and its price is strictly lower than ours by at most {limit}% of our price. Identity is verified; there are no other conditions.'
        case=f'Our price: ${price}. Competitor price: ${competitor}.'
        if not missing:case+=' Competitor inventory: '+('in stock.' if stock else 'out of stock.')
        values=[True,False] if missing else [stock];decisions=[v and reduction<=limit for v in values]
        witness=[{'competitor_in_stock':v,'eligible':d} for v,d in zip(values,decisions)];question='Does this price match qualify?'
    if missing and index%2:case+=' The decisive field, if not listed, is not available; do not assume a default value.'
    truth=decisions[0] if len(set(decisions))==1 else None
    assert (truth is None)==(variant=='unknown')
    if variant=='yes':assert truth is True
    if variant=='no':assert truth is False
    layout=index%3
    state=policy+'\nCase: '+case if layout==0 else {'policy':policy,'case':case} if layout==1 else 'SERVICE DESK NOTE\n'+case+'\nAPPLICABLE RULE\n'+policy
    q=choice(rng,question+' Use only the supplied facts.',ANS[truth],list(ANS.values()))
    return record('insufficient',index,state,{'decision':q},{'scenario':scenario,'variant':variant,'witnesses':witness},scenario+'__'+variant,
                  '可行事实补全：'+dump(witness)+'；结论：'+ANS[truth])

DOMAINS=[
 ('equipment',[('camera impact','camera','lens unit'),('projector failure','projector','battery module'),('microphone liquid damage','microphone','wireless capsule'),('stage panel damage','stage panel','sign plate')]),
 ('shipment',[('parcel impact','parcel','glass insert'),('refrigeration breakdown','cooler','temperature probe'),('container water damage','container','paper label stock'),('handling equipment damage','handcart','caster set')]),
 ('laboratory',[('spectrometer electrical failure','spectrometer','sensor module'),('sample freezer breakdown','sample freezer','control board'),('lab bench impact','lab bench','glass top'),('pump liquid damage','pump','seal assembly')]),
 ('exhibition',[('display impact','display','screen panel'),('lighting electrical failure','lighting unit','driver board'),('speaker damage','speaker','tweeter'),('booth water damage','booth','fabric panel')]),
 ('appliance',[('washer breakdown','washer','valve assembly'),('oven electrical failure','oven','thermostat'),('refrigerator failure','refrigerator','fan module'),('cleaner impact','cleaner','brush head')]),
 ('workshop',[('lathe breakdown','lathe','drive unit'),('drill electrical failure','drill','battery pack'),('compressor failure','compressor','pressure switch'),('workbench impact','workbench','vise jaw')]),
]

def contract(index,target,rng):
    domain,types=DOMAINS[index%len(DOMAINS)];selected=rng.randrange(4)
    before=bool(index%2);benefits=[]
    for i,(event,item,part) in enumerate(types):
        cap=rng.choice([800,1000,1500,2000,2500]);fee=rng.choice([25,50,75,100]);sub=rng.choice([200,300,400,500])
        benefits.append({'code':f'B{i+1}','event':event,'item':item,'part':part,'cap':cap,'fee':fee,'sub':sub,'waiting':rng.choice([0,7,14]),'purchased':True,'usage_limit':rng.choice([500,800,1000])})
    b=benefits[selected];notice=rng.choice([10,14,21,30]);start=date(2028,rng.randint(1,11),rng.randint(1,20))
    elapsed=b['waiting']+rng.randint(2,25);delay=rng.randint(0,notice)
    ispart=target=='pay_sublimit';loss=(b['sub'] if ispart else b['cap'])+b['fee']+rng.randint(20,300)
    if target=='pay_loss':loss=rng.randint(b['fee']+10,b['cap']-1)
    use=b['usage_limit'];unsafe=False;exception=False
    if target=='not_purchased':b['purchased']=False
    if target=='waiting':b['waiting']=rng.choice([7,14]);elapsed=b['waiting']-1
    if target=='late':delay=notice+1
    if target=='usage':use=b['usage_limit']+1
    if target=='unsafe':unsafe=True
    if target=='pay_loss' and index%3==0:unsafe=exception=True
    incident=start+timedelta(days=elapsed);reported=incident+timedelta(days=delay)
    item=b['part'] if ispart else b['item']
    clauses=[]
    arithmetic=('Subtract the deductible from eligible loss first, flooring at zero. Apply the benefit limit and any applicable part sublimit to the remaining loss.' if before else
                'First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero.')
    clauses.append('GENERAL SETTLEMENT RULE\n'+arithmetic+' A part sublimit is an additional ceiling, not money added to the benefit limit. Apply exactly one deductible per claim. '+
        'For a positive payment, select "part ceiling" if the part sublimit binds strictly below the amount entering the cap operation; otherwise select "benefit ceiling" if the benefit limit binds strictly below that amount; otherwise select "loss based". A tie with loss is loss based. These definitions apply to the actual order of operations above.')
    for c in benefits:
        clauses.append(f"BENEFIT {c['code']}: {c['event']}\nThis benefit applies only to the named event {c['event']}. A claim for a complete {c['item']} and a claim for its {c['part']} both use this benefit. Its limit is {cash(c['cap'])}; deductible {cash(c['fee'])}; the part sublimit is {cash(c['sub'])} and applies only when the claimed item is the {c['part']}. The complete item has no part sublimit. Waiting period: {c['waiting']} elapsed calendar days after inception; a loss on the boundary day is eligible. Usage above {c['usage_limit']} hours excludes the loss; exactly that usage is allowed. Usage is measured at incident time.\n"+
            f"The {c['part']} sublimit cannot be borrowed by a claim under another benefit. Related accessory mentions do not change which item was damaged. Cosmetic damage with no functional loss and ordinary wear are excluded. A technician-confirmed sudden functional failure or accidental impact of the named kind can qualify, subject to all other conditions. Repair and replacement are alternative bases, not cumulative payments; the stated eligible loss already uses the approved basis. Do not add accessory costs that are not part of that loss.")
    clauses.append('SCHEDULE AND DATES\nInception: '+str(start)+'. '+ '; '.join(c['code']+': '+('purchased' if c['purchased'] else 'not purchased') for c in benefits)+'. '
        f'Report each incident within {notice} elapsed calendar days, inclusive. Same-day reporting counts as zero; weekends count. Claims concern one item and one incident. The incident occurs before policy expiry. The contract has no exhausted annual aggregate or prior claim deduction. Purchase status is determined by this schedule, not by the mere presence of a benefit description.')
    clauses.append('UNSAFE-STORAGE EXCLUSION AND EXCEPTION\nAn unsafe-storage flag excludes an otherwise covered loss. However, a signed pre-incident storage waiver removes this exclusion for that incident. A post-incident signature is not enough. The waiver affects only unsafe storage; it cannot waive waiting periods, usage limits, purchase status or late reporting. A normal-storage flag never needs a waiver. The incident file explicitly records both the storage status and waiver timing.')
    clauses.append('DECISION PRIORITY\nCheck denials in this order: benefit not purchased; incident within waiting period; usage over the benefit maximum; unsafe storage without a valid waiver; report beyond the notice window. Stop at the first applicable reason. If none applies, calculate the payment using the settlement rule. Claims here have no wear or cosmetic-only damage. Do not invent additional exclusions from external insurance practice. These are the complete fictional rules for this file.')
    clauses.append('ACCOUNTING AND DOCUMENTS\nEligible loss is the approved dollar amount after salvage and depreciation; do not deduct them again. Taxes are included. Deductibles are not premiums, and no premium is recoverable as part of the loss. All currency amounts use US dollars with no exchange conversion. A repaired part remains in its stated category even if a different supplier provided it. Inspection dates, reporting dates and incident dates have different purposes: use the incident date for waiting and the report-minus-incident interval for notice. A preliminary email does not replace the reported date in the file. The listed documents are accepted and no further document requirement remains to resolve.')
    clauses.append('OTHER BENEFITS AND ALLOCATION\nA complete-item claim is assessed under its event mapping even when the same workshop owns other insured equipment. The highest dollar limit in this document is not a selectable alternative. Where two items share a room, damage to one does not create a claim for the other. There is no stacking of benefit limits, no replacement of a part sublimit by a full-item limit, and no deduction of another benefit\'s deductible. A beneficiary may not reclassify a component as a whole item to obtain a larger ceiling. All facts needed to identify the single claimed item are in the incident file.')
    rng.shuffle(clauses)
    state='CONTRACT '+domain.upper()+'\n\n'+'\n\n'.join(clauses)
    state+=f"\n\nINCIDENT FILE\nEvent: {b['event']}. Claimed item: {item}. Eligible loss: {cash(loss)}. Incident: {incident}. Reported: {reported}. Usage at incident: {use} hours. Storage: "+('unsafe' if unsafe else 'normal')+'. Waiver: '+('signed before incident' if exception else 'none')+'. Sudden functional damage confirmed; no ordinary wear or cosmetic-only issue.'
    denials=[]
    if not b['purchased']:denials.append('not purchased')
    if elapsed<b['waiting']:denials.append('waiting period')
    if use>b['usage_limit']:denials.append('usage maximum')
    if unsafe and not exception:denials.append('unsafe storage')
    if delay>notice:denials.append('late report')
    assert len(denials)<=1
    entering=max(0,loss-b['fee']) if before else loss
    ceiling=min(b['cap'],b['sub'] if ispart else b['cap'])
    payment=min(entering,ceiling) if before else max(0,min(entering,ceiling)-b['fee'])
    reason='loss based' if entering<=ceiling else 'part ceiling' if ispart else 'benefit ceiling'
    if denials:payment=0;reason=denials[0]
    assert (payment>0)==target.startswith('pay_')
    expected_reason={'pay_loss':'loss based','pay_limit':'benefit ceiling','pay_sublimit':'part ceiling','not_purchased':'not purchased','waiting':'waiting period','late':'late report','usage':'usage maximum','unsafe':'unsafe storage'}[target]
    assert reason==expected_reason
    qs={'amount':choice(rng,'What payment is due?',cash(payment),[cash(0),cash(loss),cash(b['cap']),cash(b['fee']),cash(max(0,payment-b['fee'])),cash(payment+b['fee'])]),
        'reason':choice(rng,'Select the controlling reason under the policy definitions.',reason,list(['loss based','part ceiling','benefit ceiling','not purchased','waiting period','usage maximum','unsafe storage','late report']))}
    facts={'benefits':benefits,'selected':selected,'before':before,'loss':loss,'ispart':ispart,'elapsed':elapsed,'delay':delay,'notice':notice,'use':use,'unsafe':unsafe,'exception':exception,'expected_payment':payment,'expected_reason':reason,'domain':domain}
    return record('policy',index,state,qs,facts,target,f'事件适用{b["code"]}；先扣免赔={before}；限额{ceiling}，免赔{b["fee"]}，损失{loss}，赔付{payment}；理由{reason}。')

def main():
    out=OUT/'components';out.mkdir(parents=True,exist_ok=True)
    rs=[];seen=set()
    for scenario in ['return','approval','tenure','shipping','overtime','warranty','price_match']:
        for variant in ['yes','no','unknown','nondeciding']:
            for i in range(10):
                for attempt in range(100):
                    r=insufficient(len(rs),scenario,variant,random.Random(VERSION+scenario+variant+str(i)+':'+str(attempt)))
                    if r['_meta']['text_sha256'] not in seen:break
                else:raise RuntimeError('unique scenario budget exhausted')
                seen.add(r['_meta']['text_sha256']);rs.append(r)
    (out/'insufficient.candidate.jsonl').write_text(''.join(dump(r)+'\n' for r in rs))
    policies=[]
    for target,n in [('pay_loss',60),('pay_limit',60),('pay_sublimit',60),('not_purchased',24),('waiting',24),('late',24),('usage',24),('unsafe',24)]:
        for i in range(n):policies.append(contract(len(policies),target,random.Random(VERSION+target+str(i))))
    (out/'policy.candidate.jsonl').write_text(''.join(dump(r)+'\n' for r in policies))
    print(dump({'insufficient':len(rs),'policy':len(policies),'policy_chars': [min(len(r['state']) for r in policies),max(len(r['state']) for r in policies)],'insufficient_states':dict(Counter(r['_meta']['facts']['variant'] for r in rs))}))

if __name__=='__main__':main()
