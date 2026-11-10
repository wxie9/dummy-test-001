#!/usr/bin/env python3
"""300 authored long-policy contexts; distinct covers, exclusions and exceptions."""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date, timedelta
from build_targeted_v4_components import ROOT, record, choice
from build_targeted_v5 import digest
from check_targeted_v4_rules import gold, materialize

BASE=ROOT/'artifacts/kev_training_eval_20261026'
OUT=BASE/'policy_transfer_candidates_20261030'
VERSION='policy-transfer-20261030'
DOMAINS={
 'travel':{
  'covers':[('baggage theft','luggage','camera'),('emergency treatment','hospital care','dental treatment'),('trip cancellation','prepaid trip','excursion ticket'),('departure delay','delay expenses','taxi fare'),('passport loss','replacement documents','courier charge'),('rental collision','rental vehicle','windscreen'),('missed connection','rebooking expense','seat reservation'),('journey interruption','unused itinerary','rail ticket'),('sports equipment loss','sports equipment','bicycle'),('accommodation closure','replacement lodging','booking deposit'),('search assistance','rescue expense','helicopter transfer'),('personal liability','liability settlement','legal consultation')],
  'field':'trip length in days','thresholds':[21,45,60,90],'operator':'greater than','exception':'extended-trip endorsement',
  'flag':'prohibited activity','flag_definition':'the loss arose during an activity prohibited by the itinerary conditions','waiver':'specific activity permission'},
 'home':{
  'covers':[('burglary','household contents','jewellery'),('pipe escape','interior contents','antique rug'),('accidental breakage','living room furniture','glass panel'),('storm damage','domestic property','garden sculpture'),('fire damage','personal possessions','painting'),('freezer failure','frozen food','specialty food'),('key theft','lock replacement','electronic key'),('temporary displacement','temporary housing','pet boarding'),('electrical surge','home electronics','computer display'),('oil leakage','household flooring','decorative tile'),('fallen tree impact','outdoor property','greenhouse panel'),('moving damage','packed contents','musical instrument')],
  'field':'continuous vacancy days','thresholds':[20,35,50,65],'operator':'greater than','exception':'documented weekly inspection',
  'flag':'commercial premises use','flag_definition':'the premises were being used for an undeclared commercial activity','waiver':'approved business-use rider'},
 'health':{
  'covers':[('inpatient admission','hospital expense','private room supplement'),('outpatient treatment','clinic expense','diagnostic scan'),('emergency surgery','surgery expense','implant'),('dental restoration','dental expense','crown'),('vision correction','vision expense','spectacle frame'),('physiotherapy treatment','therapy expense','home session'),('ambulance transport','transport expense','air ambulance'),('specialist consultation','consultation expense','remote consultation'),('prescription dispensing','prescription expense','branded medicine'),('rehabilitation admission','rehabilitation expense','specialist device'),('hearing treatment','hearing expense','hearing aid'),('home nursing','nursing expense','overnight visit')],
  'field':'months since prior advice','thresholds':[3,6,9,12],'operator':'at most','exception':'accepted continuity endorsement',
  'flag':'outside-network provider','flag_definition':'the treatment was supplied outside the approved provider network','waiver':'documented emergency referral'},
 'device':{
  'covers':[('accidental impact','notebook computer','display panel'),('liquid spill','tablet computer','charging board'),('electrical failure','desktop computer','power supply'),('camera malfunction','digital camera','lens assembly'),('phone theft','mobile phone','memory module'),('audio breakdown','audio system','amplifier'),('console failure','game console','controller'),('printer malfunction','printer','print head'),('router failure','network router','antenna assembly'),('watch damage','smart watch','sensor module'),('projector breakdown','projector','optical module'),('drone impact','camera drone','navigation module')],
  'field':'device age in months','thresholds':[18,30,42,54],'operator':'greater than','exception':'extended-service endorsement',
  'flag':'unapproved repair facility','flag_definition':'the repair was performed by a facility outside the approved list','waiver':'written alternate-facility authorization'},
}
COUNTS={'pay_loss':40,'pay_limit':40,'pay_sublimit':40,'not_purchased':30,'waiting':30,'late':30,'threshold':30,'flag':30,'intentional':30}

def cash(n):return f'${n:.2f}'

def reason_text(code,d):
    return {
      'pay_loss':f'Pay the covered loss under {code}, with one deductible; no ceiling reduces the amount entering the cap calculation.',
      'pay_limit':f'Pay under {code} with its benefit ceiling binding; apply the single deductible in the stated order.',
      'pay_sublimit':f'Pay under {code} with its named-item sublimit binding; apply the single deductible in the stated order.',
      'not_purchased':f'Decline because cover {code} was not purchased.',
      'waiting':f'Decline because the incident precedes the end of the waiting period for {code}.',
      'late':f'Decline because notice for {code} arrived after its permitted interval.',
      'threshold':f'Decline under the {d["field"]} exclusion for {code}; its exception does not apply.',
      'flag':f'Decline under the {d["flag"]} exclusion for {code}; its exception does not apply.',
      'intentional':f'Decline because the claimant intentionally caused the loss; this exclusion has no exception.',
    }

def build(i,target,rng):
    domain=list(DOMAINS)[i%4];d=DOMAINS[domain];n=[2,4,7,10][(i//4)%4]
    covers=[]
    for j,(event,item,part) in enumerate(rng.sample(d['covers'],n)):
        cap=rng.choice([800,1200,1800,2600,4200,6500]);fee=rng.choice([30,60,90,150]);sub=rng.choice([240,360,480,600])
        covers.append(dict(code=f'C{j+1}',event=event,item=item,part=part,cap=cap,fee=fee,sub=sub,waiting=rng.choice([5,10,15,20]),notice=rng.choice([7,14,21,28]),threshold=rng.choice(d['thresholds']),purchased=True))
    b=rng.choice(covers);code=b['code'];before=rng.choice([True,False]);part=target=='pay_sublimit' or (target!='pay_limit' and rng.random()<.35);loss=rng.randint(b['fee']+5,min(b['cap'],b['sub'])-1) if target=='pay_loss' else (b['sub'] if part else b['cap'])+b['fee']+rng.randint(10,700)
    inception=date(2030,rng.randint(1,10),rng.randint(5,20));elapsed=b['waiting']+rng.randint(0,50);delay=rng.randint(0,b['notice'])
    threshold_trigger=rng.choice([True,False]);threshold_waiver=threshold_trigger
    if d['operator']=='greater than':value=b['threshold']+(rng.randint(1,7) if threshold_trigger else -rng.randint(0,3))
    else:value=b['threshold']-rng.randint(0,min(2,b['threshold'])) if threshold_trigger else b['threshold']+rng.randint(1,5)
    flag=rng.choice([True,False]);flag_waiver=flag;intentional=False
    if target=='not_purchased':b['purchased']=False
    elif target=='waiting':elapsed=b['waiting']-1
    elif target=='late':delay=b['notice']+1
    elif target=='threshold':
        threshold_trigger=True;threshold_waiver=False;value=b['threshold']+1 if d['operator']=='greater than' else b['threshold']
    elif target=='flag':flag=True;flag_waiver=False
    elif target=='intentional':intentional=True
    # Other covers may be unpurchased; their schedules cannot be used for this claim.
    for c in covers:
        if c is not b:c['purchased']=rng.choice([True,True,False])
    incident=inception+timedelta(days=elapsed);reported=incident+timedelta(days=delay)
    sections=[]
    for c in covers:
        sections.append(f'[Cover {c["code"]}] {c["event"]}\n'
          f'This cover responds only to {c["event"]}. Its whole-item category is {c["item"]}. Its named-item category is {c["part"]}; a loss to that named item belongs to this cover even when it is an attachment to a larger item. '
          f'Benefit ceiling: {cash(c["cap"])}. One deductible: {cash(c["fee"])}. Named-item sublimit: {cash(c["sub"])}. The sublimit applies only to {c["part"]}; all other items in this cover use only the benefit ceiling. '
          f'Waiting interval: {c["waiting"]} elapsed days from inception. An incident on the final waiting boundary is eligible. Notice interval: {c["notice"]} elapsed days from incident to report, inclusive. '
          f'Threshold exclusion: {d["field"]} {d["operator"]} {c["threshold"]}. Exception: {d["exception"]} accepted for this cover removes only that threshold exclusion. '
          f'Flag exclusion: {d["flag"]}. This means {d["flag_definition"]}. Exception: {d["waiver"]} accepted for this cover removes only that flag exclusion. '
          'An exception to one exclusion does not waive another exclusion, a waiting period, a notice deadline or purchase status. '
          'The event, item and incident must all belong to the same cover; another section cannot supply a higher limit or a smaller deductible. '
          'Costs for a whole item and its named component are alternative descriptions of the same loss and cannot be added together. '
          'The approved loss in the claim file is already adjusted for salvage, depreciation, taxes and any recoveries. These adjustments must not be deducted a second time.')
    arithmetic=('Subtract one deductible from approved loss, flooring at zero, then cap the remainder by the applicable ceilings.' if before else 'Cap approved loss by the applicable ceilings first, then subtract one deductible, flooring at zero.')
    sections += [
      '[Settlement calculation]\n'+arithmetic+' The applicable ceiling is the lesser of the benefit ceiling and any named-item sublimit. For whole-item claims there is no named-item ceiling. A ceiling binds only when it is strictly below the amount entering the cap operation; equality is not a binding ceiling. When no ceiling binds, use the loss-based settlement description. If both ceilings are present, the smaller ceiling supplies the settlement description. Pay once per incident; there is no stacking or extra deductible from another cover.',
      '[Purchase schedule]\nInception date: '+str(inception)+'.\n'+'\n'.join(c['code']+' purchase status: '+('included' if c['purchased'] else 'not included')+'.' for c in covers)+'\nA description of a cover is not proof it was purchased. Only the status above establishes inclusion. The policy remains in force on the incident date. Limits have not been reduced by earlier claims and no aggregate exhaustion applies.',
      '[Common exclusions and order]\nAn intentionally caused loss is excluded and has no exception. If more than one denial applies, use this priority: not purchased; waiting interval; late notice; threshold exclusion; flag exclusion; intentional loss. If no denial applies, settle the amount using the calculation section. All rules governing this fictional claim are stated here; no outside customary exclusions or unstated document requirements apply.',
      '[Dates and evidence]\nElapsed days are calendar date differences, with the start date counted as zero. Weekends are included. Use incident minus inception for the waiting interval and report minus incident for notice. A repair appointment or an earlier estimate is not the report date. The claim facts below are accepted findings, not allegations requiring further proof. A listed accepted exception is valid for this incident and the specified cover. A not-accepted exception supplies no waiver.',
      '[Allocation of the claim]\nOnly the single event and item named in the claim file are being claimed. Other covers remain in the booklet so the reader can distinguish similar but inapplicable benefits. Their purchase status, waiting intervals, exclusions and limits do not alter this claim. A reference to a part in another section does not reclassify the item in this file. The claimed amount contains no unrelated fees, future losses or duplicate invoices. There is no currency conversion and all amounts are US dollars.',
    ]
    rng.shuffle(sections)
    claim=(f'Event: {b["event"]}. Claimed item: {b["part"] if part else b["item"]}. Approved loss: {cash(loss)}. '
           f'Incident date: {incident}. Report date: {reported}.\n'
           f'Measured {d["field"]}: {value}. {d["exception"]}: '+('accepted' if threshold_waiver else 'not accepted')+'.\n'
           f'{d["flag"]}: '+('present' if flag else 'absent')+f'. {d["waiver"]}: '+('accepted' if flag_waiver else 'not accepted')+'.\n'
           'Intentional loss: '+('yes' if intentional else 'no')+'. All exception statuses in this file refer to '+code+'.')
    state='POLICY DOMAIN: '+domain+'\n\n'+'\n\n'.join(sections)+'\n\n[Claim facts]\n'+claim
    denials=[]
    if not b['purchased']:denials.append('not_purchased')
    if elapsed<b['waiting']:denials.append('waiting')
    if delay>b['notice']:denials.append('late')
    if threshold_trigger and not threshold_waiver:denials.append('threshold')
    if flag and not flag_waiver:denials.append('flag')
    if intentional:denials.append('intentional')
    assert len(denials)<=1
    entering=max(0,loss-b['fee']) if before else loss;ceiling=min(b['cap'],b['sub']) if part else b['cap']
    amount=min(entering,ceiling) if before else max(0,min(entering,ceiling)-b['fee'])
    reason='pay_loss' if entering<=ceiling else 'pay_sublimit' if part else 'pay_limit'
    if denials:amount=0;reason=denials[0]
    assert reason==target and (amount>0)==target.startswith('pay_')
    texts=reason_text(code,d);wrong=[v for k,v in texts.items() if k!=reason];rng.shuffle(wrong)
    # Four plausible numeric alternatives, including incorrect order and ignored caps.
    alternatives=list(dict.fromkeys(cash(x) for x in [0,loss,max(0,loss-b['fee']),b['cap'],b['sub'],min(max(0,loss-b['fee']),ceiling),max(0,min(loss,ceiling)-b['fee']),amount+b['fee'],max(0,amount-b['fee'])] if x!=amount))
    rng.shuffle(alternatives)
    qs={'reason':choice(rng,'Which settlement outcome follows from this policy?',texts[reason],wrong[:4]),
        'amount':choice(rng,'What dollar amount is payable for this claim?',cash(amount),alternatives[:4])}
    return record('policy',i,state,qs,{'domain':domain,'target':target,'cover_count':n,'named_item_claim':part,'deduct_before_cap':before,'selected_code':code,'threshold_trigger':threshold_trigger,'threshold_exception':threshold_waiver,'flag_trigger':flag,'flag_exception':flag_waiver,'expected_payment':amount},target,'按事件定位保障，检查排除与各自例外，再按规定次序扣免赔并应用限额。')

def solve_visible(state):
    policy,claim=state.split('[Claim facts]\n');domain=re.search(r'POLICY DOMAIN: (\w+)',policy)[1];d=DOMAINS[domain]
    def get(pattern,s):
        m=re.search(pattern,s);assert m,pattern
        return m[1]
    event=get(r'Event: ([^.]+)\.',claim);item=get(r'Claimed item: ([^.]+)\.',claim)
    sections=re.findall(r'\[Cover (C\d+)\] ([^\n]+)\n(.*?)(?=\n\n|\Z)',policy,re.S)
    selected=[(code,body) for code,title,body in sections if title==event];assert len(selected)==1
    code,s=selected[0]
    number=lambda key:int(get(re.escape(key)+r': \$(\d+)\.00',s))
    cap,fee,sub=number('Benefit ceiling'),number('One deductible'),number('Named-item sublimit')
    part=get(r'named-item category is ([^;]+);',s);whole=get(r'whole-item category is ([^.]+)\.',s);assert item in [part,whole]
    waiting=int(get(r'Waiting interval: (\d+)',s));notice=int(get(r'Notice interval: (\d+)',s))
    field,op,limit=re.search(r'Threshold exclusion: (.+?) (greater than|at most) (\d+)\.',s).groups()
    threshold_exception=get(r'Exception: ([^.]+?) accepted for this cover removes only that threshold exclusion',s)
    flag_name=get(r'Flag exclusion: ([^.]+)\.',s)
    flag_exception=get(r'Exception: ([^.]+?) accepted for this cover removes only that flag exclusion',s)
    value=int(get('Measured '+re.escape(field)+r': (\d+)',claim));trigger=value>int(limit) if op=='greater than' else value<=int(limit)
    threshold_ok=get(re.escape(threshold_exception)+r': (accepted|not accepted)',claim)=='accepted'
    flag=get(re.escape(flag_name)+r': (present|absent)',claim)=='present'
    flag_ok=get(re.escape(flag_exception)+r': (accepted|not accepted)',claim)=='accepted'
    inception=date.fromisoformat(get(r'Inception date: ([\d-]+)',policy));incident=date.fromisoformat(get(r'Incident date: ([\d-]+)',claim));reported=date.fromisoformat(get(r'Report date: ([\d-]+)',claim))
    purchased=get(code+r' purchase status: (included|not included)',policy)=='included';intentional=get(r'Intentional loss: (yes|no)',claim)=='yes'
    violations=[('not_purchased',not purchased),('waiting',(incident-inception).days<waiting),('late',(reported-incident).days>notice),('threshold',trigger and not threshold_ok),('flag',flag and not flag_ok),('intentional',intentional)]
    reason=next((k for k,v in violations if v),None)
    if reason:return texts_from_visible(code,field,flag_name)[reason],0
    loss=int(get(r'Approved loss: \$(\d+)\.00',claim));before='Subtract one deductible from approved loss' in policy
    ceiling=sub if item==part and sub<cap else cap
    if before:
        net=max(0,loss-fee);amount=min(net,ceiling);binds=net>ceiling
    else:amount=max(0,min(loss,ceiling)-fee);binds=loss>ceiling
    reason='pay_sublimit' if binds and item==part and sub<cap else 'pay_limit' if binds else 'pay_loss'
    return texts_from_visible(code,field,flag_name)[reason],amount

def texts_from_visible(code,field,flag):
    # Only visible names are used to reconstruct the candidate descriptions.
    return reason_text(code,{'field':field,'flag':flag})

def verify(r):
    expected,amount=solve_visible(r['state']);assert gold(r,'reason')==expected;assert gold(r,'amount')==cash(amount)
    materialize(r)

def main():
    OUT.mkdir(exist_ok=True);seen=set()
    for path in list((ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl'))+[BASE/'targeted_v6_20261030/train.jsonl',BASE/'targeted_v6_20261030/development.jsonl']:
        seen.update(digest(json.loads(l)['state']) for l in path.read_text().splitlines())
    manifest={'status':'component_only_not_trained','planned_train_contexts':300,'files':{},'limitations':['Authored fictional policies, not official benchmark examples.','Same-author separate visible-text checker is not independent external review.','Official test coverage informed design; future evaluation is not blind generalization.','Fresh cases, question options and text coverage change together.']}
    for split,factor in [('train',1),('development',.2)]:
        rows=[];rejected=0
        for target,n in COUNTS.items():
            for j in range(int(n*factor)):
                i=len(rows)
                for attempt in range(10000):
                    r=build(i,target,random.Random(f'{VERSION}/{split}/{target}/{j}/{attempt}'));h=digest(r['state'])
                    if h not in seen:break
                else:raise AssertionError('No new policy found')
                seen.add(h);m=r['_meta'];m.update(id=f'{VERSION}/{split}/{target}/{j}',group_id=f'{VERSION}/{split}/{target}/{j}',source=VERSION,split=split,text_sha256=h)
                for q in r['questions'].values():q['src']=VERSION
                verify(r)
                for qname,q in r['questions'].items():
                    for k in q['criteria']:
                        if k==q['label']:continue
                        bad=copy.deepcopy(r);bad['questions'][qname]['label']=k
                        try:verify(bad)
                        except AssertionError:rejected+=1
                        else:raise AssertionError('Wrong label accepted')
                rows.append(r)
        random.Random(VERSION+split).shuffle(rows);p=OUT/(split+'.candidate.jsonl');p.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
        for line in p.read_text().splitlines():
            r=json.loads(line);r['_meta']['facts']={};verify(r)
        lengths=sorted(len(r['state']) for r in rows)
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'targets':dict(Counter(r['_meta']['subtype'] for r in rows)),'domains':dict(Counter(r['_meta']['facts']['domain'] for r in rows)),'cover_counts':dict(Counter(r['_meta']['facts']['cover_count'] for r in rows)),'deduct_before_cap':dict(Counter(str(r['_meta']['facts']['deduct_before_cap']) for r in rows)),'text_chars_five_number':[lengths[0],lengths[len(lengths)//4],lengths[len(lengths)//2],lengths[3*len(lengths)//4],lengths[-1]],'incorrect_labels_rejected':rejected,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        (OUT/(split+'.examples.json')).write_text(json.dumps([next(r for r in rows if r['_meta']['subtype']==k) for k in COUNTS],ensure_ascii=False,indent=2)+'\n')
    manifest['checks']={'visible_labels_recomputed_without_latent_facts':True,'normalized_train_development_prior_v6_frozen_test_overlap':0}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
