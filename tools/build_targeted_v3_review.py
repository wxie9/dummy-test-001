#!/usr/bin/env python3
"""Author a small, auditable four-family pilot; preserve the other three verbatim.

This produces review candidates, NOT a balanced training split. No benchmark
question is used as a training row. The design is informed by inspected errors.
"""
import hashlib
import json
import random
from collections import Counter
from datetime import date
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/kev_training_eval_20261026'
OUT = BASE / 'targeted_v3_review_20261029'
OLD = BASE / 'targeted_v2_all7_compact'
VERSION = 'targeted-v3-review-20261029'
RECORDS = []


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def state_hash(state):
    return digest(canonical(state).encode())


def pct(value):
    return f'{float(value * 100):.2f}%'


def dollars(cents):
    return f'${cents / 100:,.2f}'


def row(family, subtype, state, explanation, facts=None, group=None):
    ordinal = sum(x['_meta']['family'] == family for x in RECORDS)
    rid = f'{VERSION}/{family}/review/{ordinal:03d}'
    r = {'state': state, 'questions': {}, '_meta': {
        'id': rid, 'family': family, 'subtype': subtype, 'split': 'review',
        'source': VERSION, 'group_id': f'{VERSION}/{family}/{group or subtype}',
        'facts': facts or {}, 'review_zh': explanation, 'option_values': {},
        'expected_answers': {}, 'text_sha256': state_hash(state),
    }}
    RECORDS.append(r)
    return r


def choice(r, key, prompt, gold, distractors):
    values = list(dict.fromkeys([gold] + distractors))
    assert len(values) >= 3, (key, values)
    random.Random(r['_meta']['id'] + ':' + key).shuffle(values)
    options = {chr(97 + i): v for i, v in enumerate(values)}
    label = next(k for k, v in options.items() if v == gold)
    r['questions'][key] = {'type': 'choice', 'instructions': prompt,
        'criteria': options, 'label': label, 'src': VERSION}
    r['_meta']['option_values'][key] = options
    r['_meta']['expected_answers'][key] = gold


def probability_q(r, key, prompt, value, handwritten_percent):
    assert pct(value) == handwritten_percent, (key, value, handwritten_percent)
    others = [pct(1-value), '0.00%', '25.00%', '50.00%', '75.00%', '100.00%']
    choice(r, key, prompt + ' Round to two decimal places in percent.', pct(value),
           list(dict.fromkeys(v for v in others if v != pct(value)))[:3])


def bucket_q(r, value, boundaries):
    bounds = list(map(F, boundaries))
    labels = [f'[{bounds[i]}%, {bounds[i+1]}%' + (']' if i == len(bounds)-2 else ')')
              for i in range(len(bounds)-1)]
    idx = next(i for i in range(len(bounds)-1)
               if bounds[i] <= value * 100 and
               (value * 100 < bounds[i+1] or i == len(bounds)-2))
    r['questions']['bucket'] = {'type': 'score', 'instructions':
        'Select the interval containing the posterior probability of a true incident given an alert. '
        'Square brackets include an endpoint; round brackets exclude it. Use the exact probability.',
        'criteria': labels, 'label': idx, 'src': VERSION}
    r['_meta']['expected_answers']['bucket'] = labels[idx]
    r['questions']['more_likely'] = {'type': 'noul', 'instructions':
        'Given an alert, is a true incident strictly more likely than no true incident?',
        'label': value > F(1, 2), 'src': VERSION}
    r['_meta']['expected_answers']['more_likely'] = value > F(1, 2)


def make_probability():
    for subtype, numbers, hand in [
        ('conditional_table', [18, 42, 54, 36], ['30.00%', '25.00%']),
        ('conditional_prose', [21, 39, 14, 56], ['35.00%', '60.00%']),
    ]:
        a,b,c,d = numbers
        state = ('A return audit counts every item once.\n'
                 f'| Depot | Returned | Kept |\n| North | {a} | {b} |\n| South | {c} | {d} |'
                 if subtype.endswith('table') else
                 f'North sent {a+b} parcels: {a} were returned and {b} kept. '
                 f'South sent {c+d} parcels: {c} were returned and {d} kept. '
                 'These are the only depots; no parcel has two depots.')
        r = row('probability', subtype, state,
                f'正向以 North 总数为分母：{a}/({a}+{b})={hand[0]}。'
                f'反向以全部退件为分母：{a}/({a}+{c})={hand[1]}。两问不能交换分母。',
                {'counts': numbers}, group=subtype)
        probability_q(r, 'return_given_north', 'Choose uniformly among North items. What is the probability of a return?', F(a,a+b), hand[0])
        probability_q(r, 'north_given_return', 'Choose uniformly among all returned items. What is the probability it came from North?', F(a,a+c), hand[1])
    for affected,tp,fp,hand,bounds in [
        (1200,1080,440,'71.05%',[0,10,30,50,70,90,100]),
        (200,180,490,'26.87%',[0,20,40,60,80,100]),
    ]:
        r = row('probability', 'bayes_base_rate',
            f'An audit covers 10,000 login sessions. Exactly {affected} are true incidents; '
            f'{tp} of those raise an alert. Among the {10000-affected} sessions without an incident, '
            f'{fp} raise an alert. A session is selected uniformly from all alerted sessions.',
            f'报警后验为 TP/(TP+FP)={tp}/({tp}+{fp})={hand}；分母不是全部会话。',
            {'population':10000,'incidents':affected,'tp':tp,'fp':fp}, group='bayes_base_rate')
        value=F(tp,tp+fp)
        probability_q(r,'posterior','What is the probability of a true incident?',value,hand)
        bucket_q(r,value,bounds)
    r=row('probability','independent_all_and_fail',
        'Three independent storage jobs succeed with probabilities 80%, 90%, and 95%. '
        'The complete batch succeeds only when all three jobs succeed.',
        '全部成功=0.8×0.9×0.95=68.40%；至少一次失败=1−0.684=31.60%。',
        {'p':['4/5','9/10','19/20']})
    value=F(4,5)*F(9,10)*F(19,20)
    probability_q(r,'all','What is the probability that every job succeeds?',value,'68.40%')
    probability_q(r,'any_fail','What is the probability that at least one job fails?',1-value,'31.60%')
    r=row('probability','independent_any',
        'Two independent radio links deliver a packet with probabilities 40% and 70%. '
        'The packet arrives if either or both links deliver it.',
        '至少一条成功=1−(1−0.4)(1−0.7)=82.00%。',{'p':['2/5','7/10']})
    probability_q(r,'any','What is the probability that the packet arrives?',1-F(3,5)*F(3,10),'82.00%')
    for op,p,q,target,expected in [
        ('AND',F(3,5),F(4,5),F(1,2),'second'),
        ('OR',F(1,2),F(3,5),F(4,5),'equal'),
        ('OR',F(3,10),F(1,2),F(3,5),'first'),
    ]:
        value=p*q if op=='AND' else 1-(1-p)*(1-q)
        actual='first' if value>target else 'second' if value<target else 'equal'
        assert actual==expected
        definition='both A and B occur' if op=='AND' else 'at least one of A and B occurs'
        r=row('probability',f'compare_{op.lower()}_{expected}',
            f'Events A and B are independent, with probabilities {pct(p)} and {pct(q)}. '
            f'The first event is: {definition}. The second event has probability {pct(target)}. '
            'Only compare the two marginal probabilities; no relation between the second event and A or B is needed.',
            f'第一事件概率={pct(value)}，第二事件={pct(target)}，比较结果={expected}。',
            {'op':op,'p':str(p),'q':str(q),'target':str(target)},group=f'compare_{op.lower()}')
        wording={'first':'The first event is more likely','second':'The second event is more likely','equal':'The probabilities are equal'}
        choice(r,'compare','Which statement is correct?',wording[actual],list(wording.values()))
    specs=[
        ('expected_value_signed',{'A':([(F(2,5),600),(F(3,5),-120)],60),
          'B':([(F(7,10),260),(F(3,10),-80)],30),
          'C':([(F(1,2),360),(F(1,2),-100)],25)}, {'A':108,'B':128,'C':105},'B'),
        ('expected_value_multioutcome',{'A':([(F(1,5),900),(F(1,2),200),(F(3,10),-300)],50),
          'B':([(F(1,2),280),(F(1,2),-40)],30)}, {'A':140,'B':90},'A'),
        ('expected_value_negative',{'A':([(F(1,4),200),(F(3,4),-160)],40),
          'B':([(F(1,2),80),(F(1,2),-100)],20)}, {'A':-110,'B':-30},'B'),
    ]
    for subtype,projects,hand,winner in specs:
        lines=['Select exactly one project, maximizing expected net cash flow, even if every expectation is negative. '
               'Each project has mutually exclusive, exhaustive outcomes. Gains and losses below exclude the upfront cost; '
               'pay that cost exactly once regardless of outcome. No other costs or benefits apply.']
        expected={}
        for name,(outcomes,cost) in projects.items():
            assert sum(p for p,_ in outcomes)==1
            expected[name]=sum(p*v for p,v in outcomes)-cost
            terms=[f'{pct(p)} probability: '+('gain' if v>=0 else 'lose')+f' ${abs(v)}' for p,v in outcomes]
            lines.append(f'Project {name}: upfront cost ${cost}; '+ '; '.join(terms)+'.')
        assert expected==hand and max(expected,key=expected.get)==winner
        r=row('probability',subtype,'\n'.join(lines),
            '逐项按带符号现金流求期望，再减一次成本：'+str(hand)+f'；选择 {winner}。负期望也必须选最大者。',
            {'projects':{k:{'outcomes':[[str(p),v] for p,v in o],'cost':c} for k,(o,c) in projects.items()}},group=subtype)
        choice(r,'project','Which project has the highest expected net cash flow?',f'Project {winner}',
            [f'Project {k}' for k in projects]+['All listed projects have equal expected net cash flow'])
        correct=hand[winner]
        choice(r,'expected_net',f'What is the expected net cash flow of project {winner}?',
            f'${correct:.2f}',[f'${correct+projects[winner][1]:.2f}',f'${-correct:.2f}','$0.00'])


def make_insufficient():
    variants=['complete_yes','complete_no','unknown','missing_nondeciding']
    # The two endpoints witness the possible decisions. Bounds are all explicit
    # in the visible question; no latent assumption may resolve missing facts.
    specs={
      'return_window': (
        'A return is eligible if requested within 21 elapsed calendar days after delivery, including day 21. '
        'Every order in this file was delivered on or after its order date and on or before its request date. No other condition applies.',
        ['Order placed 2027-03-01; return requested 2027-03-30; delivered 2027-03-18.',
         'Order placed 2027-03-01; return requested 2027-03-30; delivered 2027-03-01.',
         'Order placed 2027-03-01; return requested 2027-03-30. Customer tier: bronze.',
         'Order placed 2027-03-01; return requested 2027-03-12. Delivery date was not supplied.'],
        [[12],[29],[0,29],[0,11]],'le',21,[True,False,None,True],
        '用签收日期而非下单日期计算。缺签收日时用订单日至申请日给出的范围。'),
      'approval': (
        'A payment under $300 needs no approver. A payment from $300 through $8,000 needs an actual approver at level 2 or above; '
        'above $8,000 it needs level 3. Level 1 is staff, level 2 is manager, level 3 is director. '
        'The actual approver has exactly one of these levels. A copied colleague is not an approver. Decide whether authorization is sufficient, not whether the purchase is profitable.',
        ['Payment $2,500; actual approver Mira is level 2. Leon (level 3) was copied.',
         'Payment $2,500; actual approver Mira is level 1. Leon (level 3) was copied.',
         'Payment $2,500; actual approver Mira; copied colleague Leon is level 3.',
         'Payment $120; actual approver Mira; her job level was not supplied.'],
        [[2],[1],[1,3],[1,3]],'ge',2,[True,False,None,True],
        '只能用实际审批人的权限，不能借用抄送人的职位。小额付款不依赖审批人职位。'),
      'tenure': (
        'A grant requires at least 730 elapsed days of continuous company employment by 2027-06-01. '
        'Team transfers do not reset tenure. Every person below joined the company on or before the stated team-transfer date and remained continuously employed through the application date.',
        ['Hired 2024-06-01; transferred to Search on 2026-06-01.',
         'Hired 2026-06-01; transferred to Search on 2026-06-01.',
         'Transferred to Search on 2026-06-01. Office: West.',
         'Transferred to Search on 2024-06-01. Company hire date is not listed.'],
        [[1095],[365],[365,1461],[1095,1461]],'ge',730,[True,False,None,True],
        '公司任职时间不等于团队任职时间。已知转组满三年且持续在职，即使缺入职日仍满足730天。'),
      'shipping': (
        'Free shipping applies exactly when merchandise subtotal minus merchandise discount is at least $120. '
        'The discount is between $0 and $60 inclusive. Tax and shipping fees do not enter this calculation.',
        ['Subtotal $158; merchandise discount $20; tax $8.',
         'Subtotal $158; merchandise discount $50; tax $8.',
         'Subtotal $158; tax $8. Merchandise discount is not reported.',
         'Subtotal $90; tax $8. Merchandise discount is not reported.'],
        [[138],[108],[98,158],[30,90]],'ge',120,[True,False,None,False],
        '比较的是折后金额；未知折扣取0到60的边界。小计90即使无折扣也不免邮。'),
      'overtime': (
        'Overtime occurs if total hours strictly exceed 40 in this Monday-to-Friday week. '
        'There is one shift per weekday and no weekend work. Every shift lasts from 0 to 9 hours inclusive.',
        ['Monday to Thursday hours: 9, 9, 8, 9. Friday: 8.',
         'Monday to Thursday hours: 9, 9, 8, 9. Friday: 4.',
         'Monday to Thursday hours: 9, 9, 8, 9. Friday is unreported.',
         'Monday to Thursday hours: 6, 7, 7, 7. Payroll region: East.'],
        [[43],[39],[35,44],[27,36]],'gt',40,[True,False,None,False],
        '前三例已知35小时，未知周五可能跨40阈值；最后一例最多36小时，缺周五仍确定无加班。'),
      'warranty': (
        'A warranty is valid through 2027-01-10 inclusive for an item purchased 2025-07-10. '
        'Within that window, manufacturing defects are covered and accidental damage is excluded. '
        'Every claim has exactly one of these two causes. After expiry neither cause is covered.',
        ['Claim date 2026-07-10; technician confirms manufacturing defect.',
         'Claim date 2026-07-10; technician confirms accidental damage.',
         'Claim date 2026-07-10; case ID W-824; serial number verified.',
         'Claim date 2027-03-10; cause not reported.'],
        [[1],[0],[0,1],[0,1]],'ge',1,[True,False,None,False],
        '有效期内缺原因不能判定；已过保修期时缺原因不影响拒赔。'),
      'price_match': (
        'A price match is eligible if the same item is in stock at the competitor and the competitor price is lower than ours by no more than 15% of our price. '
        'No other condition applies. The item identity is verified in every case.',
        ['Our price $240; competitor $216; competitor stock available.',
         'Our price $240; competitor $216; competitor out of stock.',
         'Our price $240; competitor $216. Stock availability is not known.',
         'Our price $240; competitor $180. Stock availability is not known.'],
        [[1],[0],[0,1],[0,1]],'ge',1,[True,False,None,False],
        '216相对240低10%，需要确认有货；180低25%已超15%，库存未知也能确定不符合。'),
    }
    for scenario,(policy,cases,domains,op,threshold,expected,note) in specs.items():
        for i,variant in enumerate(variants):
            domain=domains[i]
            def evaluate(v):
                if i==3 and scenario=='approval': return True
                if i==3 and scenario in ('warranty','price_match'): return False
                return v<=threshold if op=='le' else v>=threshold if op=='ge' else v>threshold
            possible={evaluate(v) for v in domain}
            answer=next(iter(possible)) if len(possible)==1 else None
            assert answer is expected[i]
            interpretations={True:'Yes — the stated requirement is met',False:'No — the stated requirement is not met',None:'Cannot determine from the supplied facts'}
            r=row('insufficient',scenario+'__'+variant,policy+'\nCase record: '+cases[i],
                  note+f' 本例可行判定集合={sorted(possible)}；答案={interpretations[answer]}。',
                  {'scenario':scenario,'variant':variant,'domain_witnesses':domain,'predicate':op,
                   'threshold':threshold,'possible_decisions':sorted(possible)}, group=scenario)
            choice(r,'decision','Is the stated requirement met for this case? Use only the supplied policy and facts; do not treat an absent field as false.',
                   interpretations[answer],list(interpretations.values()))


BENEFITS={
    'imaging': {'cap':180000,'fee':8000,'wait':0,'sub':{'audio recorder':42000}},
    'mechanical': {'cap':90000,'fee':6000,'wait':7,'sub':{'battery module':18000}},
    'cancellation': {'cap':320000,'fee':15000,'wait':10,'sub':{'admission ticket':60000}},
    'venue': {'cap':240000,'fee':12000,'wait':0,'sub':{'signage':30000}},
}


def policy_sections(order):
    arithmetic=(
        'Apply limits to the gross eligible loss first: take the smallest of loss, benefit limit and any applicable category sublimit; then subtract the benefit deductible once, flooring at zero.'
        if order=='after' else
        'Subtract the benefit deductible once from gross eligible loss, flooring at zero; then apply the benefit limit and any applicable category sublimit to that net amount.')
    return [
      ('1. Contract and arithmetic',
       'This is a single-claim policy, effective 2027-06-01 at the start of the day. All amounts are US dollars. '
       'Only the benefit assigned by the event-to-benefit rules can pay; do not combine limits from other benefits. '
       'The schedule marks imaging, mechanical and cancellation as purchased; venue is not purchased. '
       'Gross eligible loss in the claim record has already excluded salvage, depreciation and unrelated expenses. '
       'No taxes, exchange-rate conversion or proportional reductions remain to apply. '+arithmetic+' '
       'A category sublimit is an additional ceiling, not extra money to add to the benefit limit. '
       'For an admitted positive claim, record pay_sublimit when the category sublimit strictly determines the ceiling; '
       'otherwise record pay_limit when the benefit limit strictly determines the ceiling; otherwise record pay_loss. '
       'For deduction-before-limits, compare ceilings with net loss; for deduction-after-limits, compare them with gross loss. '
       'A tie with loss is pay_loss; a tie between binding benefit and category limits is pay_sublimit.'),
      ('2. Imaging equipment',
       'External impact, theft and accidental liquid damage to portable cameras or audio recorders map to imaging. '
       'Its per-claim limit is $1,800 and its deductible is $80. There is no waiting period. '
       'Audio recorders have a $420 category sublimit. Cameras have no category sublimit. '
       'A battery inside a camera does not change its classification when the claimed damaged item is the complete camera. '
       'For this benefit, cosmetic scratches without loss of function are excluded. Repairable functional damage is eligible. '
       'Theft from an unattended public location is excluded except when the item was inside a locked cabinet and forced-entry evidence is recorded. '
       'Both exception conditions must hold. A locked carrying bag alone does not meet the cabinet condition. '
       'This exception removes only the unattended-public-location exclusion; it does not waive notice or purchase requirements.'),
      ('3. Mechanical equipment',
       'Internal electrical or mechanical failure of a projector or a standalone projector battery module maps to mechanical. '
       'Its per-claim limit is $900 and its deductible is $60. A standalone battery module has a $180 category sublimit; '
       'a complete projector has none. The waiting period is 7 elapsed calendar days after the effective date. '
       'An event at exactly 7 elapsed days is outside the waiting period. Usage strictly above 1,000 operating hours is excluded; '
       'exactly 1,000 hours is allowed. Usage is measured at incident time, not at reporting time. '
       'Failure from ordinary wear is excluded even if usage is below 1,000 hours. '
       'For an internal electrical failure, a camera purchased for recording the event does not make imaging applicable. '
       'Replacement accessories are included only if identified in the gross eligible loss and assigned to the same damaged item.'),
      ('4. Cancellation benefit',
       'Cancellation of an entire public performance after a mandatory local closure order maps to cancellation. '
       'Its limit is $3,200 and its deductible is $150. Nonrefundable admission tickets have a $600 sublimit. '
       'There is a 10-day elapsed waiting period; day 10 is allowed. Voluntary cancellation for poor ticket sales is excluded. '
       'A partial equipment outage that leaves the performance running is not a cancellation event. '
       'Ticket refunds already received are removed before reporting eligible loss. '
       'This benefit does not pay for repairs to an individual projector or camera even when it was used at a performance.'),
      ('5. Venue property',
       'Accidental physical damage to leased staging, signage or venue furniture maps to venue. '
       'Its limit would be $2,400 with a $120 deductible and a $300 signage sublimit if purchased. '
       'There is no waiting period. The purchase schedule in section 1 controls whether it exists for this contract. '
       'Damage to a portable camera at a venue still maps to imaging; location alone does not select venue coverage. '
       'Damage to a projector arising from its internal failure remains mechanical. '
       'Loss of expected advertising revenue is not eligible physical damage and is never included in signage repair loss.'),
      ('6. Notice, precedence and evidence',
       'The report date must be no more than 10 elapsed calendar days after the incident date. '
       'Same-day reporting is 0 days; exactly 10 days is timely. Count weekends. '
       'All incidents in these files occur on or after inception and before expiry. '
       'If multiple denial conditions hold, use this exact precedence: not purchased, waiting period, exclusion, late report. '
       'Within exclusions use usage exclusion before unattended theft, then wear, then cosmetic-only damage. '
       'If no denial condition holds, use the arithmetic and payment-reason definitions in section 1. '
       'An admitted claim receives no reimbursement beyond the calculated amount. '
       'The claim record supplies every required event fact; do not infer extra misconduct or missing documents. '
       'Unmentioned loss items have zero claimed loss. Claim clerks cannot waive policy terms by adding a subject line.'),
      ('7. Record interpretation',
       'Incident and report dates use YYYY-MM-DD. Item category refers to the item claimed, not to equipment mentioned as background. '
       'The gross eligible loss is the final accepted repair or replacement figure, not a quote to be discounted again. '
       'Each file concerns one event, one item and one payment. There are no previous claims or exhausted aggregate limits. '
       'All reported figures are exact to the cent; round only a final amount if needed. '
       'A denial has payment zero, but zero is not a substitute for selecting its stated reason. '
       'Policy sections may be presented in a different physical order; their numbered cross-references and legal effect are unchanged.'),
    ]


def solve_policy(facts):
    b=BENEFITS[facts['benefit']]
    wait=(date.fromisoformat(facts['incident'])-date(2027,6,1)).days
    delay=(date.fromisoformat(facts['report'])-date.fromisoformat(facts['incident'])).days
    denials=[]
    if facts['benefit']=='venue': denials.append('deny_not_purchased')
    if wait<b['wait']: denials.append('deny_waiting')
    if facts['benefit']=='mechanical' and facts['hours']>1000: denials.append('deny_usage')
    if facts['theft'] and not(facts['locked_cabinet'] and facts['forced_entry']): denials.append('deny_theft')
    if delay>10: denials.append('deny_late')
    assert len(denials)<=1, 'pilot uses one decisive denial; precedence remains explicit'
    if denials: return 0,denials[0]
    sub=b['sub'].get(facts['item'],10**12)
    ceiling=min(b['cap'],sub)
    loss=facts['loss']
    base=loss if facts['order']=='after' else max(0,loss-b['fee'])
    payment=max(0,min(base,ceiling)-b['fee']) if facts['order']=='after' else min(base,ceiling)
    reason='pay_loss' if base<=ceiling else 'pay_sublimit' if sub<=b['cap'] else 'pay_limit'
    return payment,reason


def make_policy():
    # Independently hand-worked reference amounts, in cents; checked against solver.
    cases=[
        ('camera_limit_after',{},172000,'pay_limit'),
        ('camera_limit_before',{'order':'before'},180000,'pay_limit'),
        ('recorder_after',{'item':'audio recorder','loss':70000},34000,'pay_sublimit'),
        ('recorder_before',{'item':'audio recorder','loss':70000,'order':'before'},42000,'pay_sublimit'),
        ('camera_loss_after',{'loss':31550},23550,'pay_loss'),
        ('camera_loss_before',{'loss':31550,'order':'before'},23550,'pay_loss'),
        ('projector_limit',{'benefit':'mechanical','item':'projector','loss':110000},84000,'pay_limit'),
        ('battery_sublimit',{'benefit':'mechanical','item':'battery module','loss':24000},12000,'pay_sublimit'),
        ('theft_exception',{'loss':80000,'theft':True,'locked_cabinet':True,'forced_entry':True},72000,'pay_loss'),
        ('theft_excluded',{'loss':80000,'theft':True},0,'deny_theft'),
        ('late_report',{'loss':100000,'report':'2027-07-02'},0,'deny_late'),
        ('report_boundary',{'loss':100000,'report':'2027-06-30'},92000,'pay_loss'),
        ('waiting',{'benefit':'mechanical','item':'projector','loss':48000,'incident':'2027-06-05','report':'2027-06-06'},0,'deny_waiting'),
        ('waiting_boundary',{'benefit':'mechanical','item':'projector','loss':48000,'incident':'2027-06-08','report':'2027-06-09'},42000,'pay_loss'),
        ('not_purchased',{'benefit':'venue','item':'signage','loss':50000},0,'deny_not_purchased'),
        ('usage_excluded',{'benefit':'mechanical','item':'projector','loss':48000,'hours':1001},0,'deny_usage'),
    ]
    reasons={
        'pay_loss':'Pay: eligible loss, adjusted by the deductible, determines the payment',
        'pay_limit':'Pay: the benefit limit binds under the stated arithmetic',
        'pay_sublimit':'Pay: the item category sublimit binds under the stated arithmetic',
        'deny_not_purchased':'Deny: the applicable benefit was not purchased',
        'deny_waiting':'Deny: the incident is inside the waiting period',
        'deny_usage':'Deny: usage exceeds the allowed maximum',
        'deny_theft':'Deny: unattended public theft exclusion applies without its exception',
        'deny_late':'Deny: the report is late',
    }
    for i,(subtype,overrides,hand,reason) in enumerate(cases):
        f={'benefit':'imaging','item':'camera','loss':200000,'order':'after','hours':1000,
           'incident':'2027-06-20','report':'2027-06-25','theft':False,
           'locked_cabinet':False,'forced_entry':False}
        f.update(overrides)
        answer=solve_policy(f)
        assert answer==(hand,reason),(subtype,answer,hand,reason)
        if f['theft']:
            event=('The camera was stolen from an unattended public exhibition area. '
                   +('It was inside a locked cabinet; photographs document forced entry.' if f['locked_cabinet'] else
                     'It was on an open shelf, not in a locked cabinet; there is no forced-entry evidence.'))
        elif f['benefit']=='mechanical':
            event=f"The {f['item']} had an internal electrical failure unrelated to ordinary wear. Operating hours at incident: {f['hours']}."
        elif f['benefit']=='venue':
            event='Leased venue signage was broken by an accidental impact. The claim is for physical repair, not advertising revenue.'
        else:
            event=f"The {f['item']} was damaged by accidental external impact, with verified loss of function; the damage is not cosmetic-only."
        sections=policy_sections(f['order'])
        random.Random('policy-layout:'+str(i)).shuffle(sections)
        state='POLICY FILE\n\n'+'\n\n'.join(h+'\n'+s for h,s in sections)
        state+=f"\n\nCLAIM RECORD\n{event}\nIncident: {f['incident']}. Report: {f['report']}. Gross eligible loss: {dollars(f['loss'])}."
        b=BENEFITS[f['benefit']]
        note=(f"适用 {f['benefit']}，条款限额{dollars(b['cap'])}、免赔额{dollars(b['fee'])}；"
              f"扣免赔额顺序={f['order']}（after表示先限额再扣，before表示先扣再限额）。"
              f'手算赔付={dollars(hand)}；理由={reason}。')
        r=row('policy',subtype,state,note,f,group='contract_package_01')
        options=[dollars(v) for v in (0,f['loss'],b['cap'],b['fee'],max(0,hand+b['fee']),max(0,hand-b['fee']))]
        choice(r,'amount','What amount must this policy pay for this claim?',dollars(hand),options)
        choice(r,'reason','Which is the controlling payment or denial reason?',reasons[reason],list(reasons.values()))


def walk(start,parents):
    result=[]
    while start in parents:
        start=parents[start]
        assert start not in result, 'cycle'
        result.append(start)
    return result


def make_multihop():
    for v in range(3):
        parents={'Kite':'Birch','Birch':'Cedar','Cedar':'Delta','Delta':'Elm','Otter':'Pine'}
        qualified={'Birch':False,'Cedar':v==0,'Delta':v!=2,'Elm':True,'Pine':True}
        path=walk('Kite',parents)
        correct=next(n for n in path if qualified[n])
        assert correct==['Cedar','Delta','Elm'][v]
        links=list(parents.items());random.Random(v).shuffle(links)
        state=('A case starts at Kite. Each unit has at most one parent. Escalate along parent links and stop at the FIRST parent authorized for this case. '
               'Do not choose a higher ancestor once an authorized parent is reached. Units outside the chain cannot take the case.\n'
               +'\n'.join(f'{a} reports to {b}.' for a,b in links)+'\n'
               +'\n'.join(f'{n}: '+('authorized' if yes else 'not authorized') for n,yes in qualified.items()))
        r=row('multihop',f'nearest_authorized_{v}',state,
              '路径 Kite→Birch→Cedar→Delta→Elm；选择第一个有权限者 '+correct+'。Pine虽有权限但不在路径。',
              {'parents':parents,'qualified':qualified,'start':'Kite'},group='nearest_authorized')
        choice(r,'decision','Which unit receives the case?',correct,['Birch','Cedar','Delta','Elm','Pine'])
    for v,failed in enumerate(['Store','Cache','API']):
        edges=[('Web','API'),('API','Worker'),('Worker','Store'),('Preview','Cache'),('Cache','Store')]
        affected={failed}
        while True:
            nxt=affected|{a for a,b in edges if b in affected}
            if nxt==affected: break
            affected=nxt
        gold=', '.join(sorted(affected-{'Web','Preview'}))
        assert gold==['API, Cache, Store, Worker','Cache','API'][v]
        state=('The following are REQUIRED dependencies: “X depends on Y” means X becomes unavailable if Y is unavailable. '
               'Unavailability propagates only from a dependency to its dependents, never the reverse. There is no redundancy. '
               'All services initially work. A named failed service remains unavailable.\n'
               +'\n'.join(f'{a} depends on {b}.' for a,b in edges)
               +f'\nThe only initial failure is {failed}. Service Audit has no dependencies and nothing depends on Audit.')
        r=row('multihop',f'dependency_direction_{v}',state,
              f'初始故障={failed}，沿依赖的反方向传播到使用者；全部不可用={sorted(affected)}。答案只列题目指定内部服务。',
              {'edges':edges,'failed':failed,'affected':sorted(affected)},group='dependency_direction')
        choice(r,'decision','Among API, Worker, Store, Cache and Audit, which services are unavailable after propagation? Select the complete set.',
               gold,['API, Cache, Store, Worker','API, Worker','Store','Cache','API','API, Audit, Cache, Store, Worker'])
    for v,percent in enumerate([60,50,49]):
        ownership=[('Harbor','Iris',80),('Iris','Juniper',70),('Juniper','Larch',percent),('Moss','Larch',100-percent),('Larch','Fern',90)]
        parent={child:owner for owner,child,p in ownership if p>50}
        # Each child has at most one direct majority owner. Control follows
        # successive majority links, not a product-of-equity rule.
        chain=walk('Fern',parent)
        gold=chain[-1]
        assert gold==['Harbor','Larch','Moss'][v]
        state=('For this register, an entity controls a company only if it owns STRICTLY more than 50% of its voting shares. '
               'Control is transitive along qualifying links; do not multiply percentages. Exactly 50% is not control. '
               'The ultimate controller is the last entity reached by following majority-owner links. '
               'All ownership links are listed below; any unlisted shares are dispersed among individuals, none with control.\n'
               +'\n'.join(f'{owner} owns {p}% of {child}.' for owner,child,p in ownership))
        r=row('multihop',f'majority_control_{v}',state,
              '从Fern向控股方反向追溯：'+'→'.join(['Fern']+chain)+f'。50%不算控股；最终={gold}。',
              {'ownership':ownership,'chain':chain},group='majority_control')
        choice(r,'decision','Who is the ultimate controller of Fern under this register?',gold,['Harbor','Iris','Juniper','Larch','Moss','Fern'])
    for v in range(3):
        parents={'Queue':'Ari','Ari':'Bo','Bo':'Cy','Cy':'Dee','Dee':'Ena'}
        people={'Ari':(False,True),'Bo':(True,False),'Cy':(v==0,True),'Dee':(True,v<2),'Ena':(True,True),'Zed':(True,True)}
        chain=walk('Queue',parents)
        gold=next(n for n in chain if all(people[n]))
        assert gold==['Cy','Dee','Ena'][v]
        state=('An incident in the database scope enters Queue. Follow the escalation successor links until the FIRST person who is BOTH available and authorized for database incidents. '
               'An available person with the wrong scope must be skipped. An authorized person who is unavailable must be skipped. '
               'Do not contact people outside this chain.\n'
               +'\n'.join(f'{a} escalates to {b}.' for a,b in parents.items())+'\n'
               +'\n'.join(f'{n}: '+('available' if a else 'unavailable')+'; authorized scope: '+('database' if s else 'network only')+'.' for n,(a,s) in people.items()))
        r=row('multihop',f'conditional_escalation_{v}',state,
              '沿Queue→Ari→Bo→Cy→Dee→Ena，逐个同时检查可用与权限；Zed不在路径。首个满足者='+gold+'。',
              {'parents':parents,'people':people},group='conditional_escalation')
        choice(r,'decision','Who should handle this database incident?',gold,['Ari','Bo','Cy','Dee','Ena','Zed'])


def verify_written(path):
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows)==68
    assert len({r['_meta']['id'] for r in rows})==len(rows)
    assert len({state_hash(r['state']) for r in rows})==len(rows)
    for r in rows:
        assert state_hash(r['state'])==r['_meta']['text_sha256']
        for key,q in r['questions'].items():
            gold=r['_meta']['expected_answers'][key]
            if q['type']=='choice':
                assert len(set(q['criteria'].values()))==len(q['criteria'])
                assert q['criteria'][q['label']]==gold
            elif q['type']=='score':
                assert type(q['label']) is int
                assert q['criteria'][q['label']]==gold
            elif q['type']=='noul':
                assert type(q['label']) is bool and q['label']==gold
            else: raise AssertionError(q['type'])
    # Exact rendered-context exclusion only. This does NOT establish semantic
    # independence from the inspected hard-v1 errors or a clean held-out test.
    source_paths=[ROOT/'third_party/kev-source-20261025/evals/hard-v1/test.jsonl']
    for folder in ('targeted_v1','targeted_v2_probability_policy','targeted_v2_all7_compact'):
        source_paths.extend(sorted((BASE/folder).glob('*.jsonl')))
    blocked=set()
    for p in source_paths:
        for line in p.read_text().splitlines():
            obj=json.loads(line)
            if 'state' in obj: blocked.add(state_hash(obj['state']))
    assert not blocked.intersection(r['_meta']['text_sha256'] for r in rows)
    counts=Counter(r['_meta']['family'] for r in rows)
    assert counts=={'probability':12,'insufficient':28,'policy':16,'multihop':12}
    insufficient=[r for r in rows if r['_meta']['family']=='insufficient']
    assert sum(len(r['_meta']['facts']['possible_decisions'])==2 for r in insufficient)==7
    policies=[r for r in rows if r['_meta']['family']=='policy']
    assert sum(solve_policy(r['_meta']['facts'])[0]>0 for r in policies)==11
    return rows,source_paths


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    make_probability(); make_insufficient(); make_policy(); make_multihop()
    newpath=OUT/'new_four_families.review.jsonl'
    newpath.write_text(''.join(canonical(r)+'\n' for r in RECORDS))
    rows,excluded=verify_written(newpath)
    retained={}
    for split in ('train','development','test'):
        source=OLD/(split+'.jsonl')
        raw=source.read_bytes().splitlines(keepends=True)
        selected=[line for line in raw if json.loads(line)['_meta']['family'] in ('tool_routing','temporal','injection')]
        path=OUT/'retained'/(split+'.jsonl');path.parent.mkdir(exist_ok=True)
        path.write_bytes(b''.join(selected))
        assert path.read_bytes()==b''.join(selected)
        counts=Counter(json.loads(line)['_meta']['family'] for line in selected)
        expected={'tool_routing':900,'temporal':800,'injection':600} if split=='train' else {'tool_routing':100,'temporal':100,'injection':100}
        assert counts==expected
        retained[split]={'records':len(selected),'by_family':dict(counts),'sha256':digest(path.read_bytes()),
                         'source_sha256':digest(source.read_bytes()),'byte_identical_to_source_subset':True}
    question_types=Counter(q['type'] for r in rows for q in r['questions'].values())
    coverage={
        'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),
        'by_family':dict(Counter(r['_meta']['family'] for r in rows)),
        'subtypes':dict(Counter(r['_meta']['subtype'] for r in rows)),
        'question_types':dict(question_types),
        'insufficient':{'unknown':7,'complete_yes':7,'complete_no':7,'missing_nondeciding':7},
        'policy':{'positive':11,'zero':5,'deductible_before_limits':3,'deductible_after_limits':13,
                  'min_chars':min(len(r['state']) for r in rows if r['_meta']['family']=='policy'),
                  'max_chars':max(len(r['state']) for r in rows if r['_meta']['family']=='policy')},
        'verification':{'written_schema_and_options':'passed','hand_reference_vs_solver':'passed',
                        'exact_overlap_with_listed_sources':0,'source_files_checked':len(excluded),
                        'independent_model_review':False,'training_started':False},
    }
    (OUT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    manifest={'version':VERSION,'stage':'review_pilot_not_training_split',
        'new_four_families':{'file':newpath.name,'sha256':digest(newpath.read_bytes()),'contexts':len(rows)},
        'unchanged_three_families':retained,
        'checked_sources':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p.read_bytes())} for p in excluded],
        'split_policy':'All related contrasts are review-only. When expanding, assign scenario/contract/graph groups to one split before rendering; do not randomly split sibling records.',
        'assembly_status':'Do not append 68 review contexts to 2300 retained train rows: that would severely underweight the four repaired families. No train.jsonl assembled.',
        'reference_v2_train_quotas':{'tool_routing':900,'temporal':800,'injection':600,'probability':1400,'insufficient':700,'multihop':800,'policy':1200},
        'scale_note':'Quotas are an old reference, not a commitment to generate 6400 rows. Agree size after reviewing the pilot; preserve relative weights if using smaller repaired families.',
        'provenance':'New synthetic scenarios authored for audited mechanisms. Hard-v1 errors were inspected during design; subsequent scores there measure repair on a known diagnostic set, not untouched-test generalization.',
        'limitations':['Pilot has limited authored scenario and contract diversity.','Exact context exclusion cannot prove semantic non-overlap.',
                       'Author review plus deterministic checks is not independent LLM or human annotation.','No new training or evaluation performed.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    doc=['# Kev 续训 v3：四类重做样题与标注依据\n',
         '这是逐题审阅稿，不是正式训练集。正文保留模型会看到的英文题面，中文解释和事实结构仅供审阅，不进入模型输入。',
         '四类共68条情境；相同情境的多问不是独立样本。其余三类保持v2原始记录。未启动训练。\n']
    for i,r in enumerate(rows,1):
        doc += [f"## {i}. {r['_meta']['family']} / {r['_meta']['subtype']}\n",f"ID：`{r['_meta']['id']}`\n",'```text',r['state'],'```\n']
        for key,q in r['questions'].items():
            doc += [f"**{key} ({q['type']})**：{q['instructions']}\n"]
            if q['type']=='choice': doc += [f'- {k}: {v}' for k,v in q['criteria'].items()]
            elif q['type']=='score': doc += [f'- {k}: {v}' for k,v in enumerate(q['criteria'])]
            doc += [f"\n正确标签：`{q['label']}`；含义：{r['_meta']['expected_answers'][key]}\n"]
        doc += ['标注依据：'+r['_meta']['review_zh']+'\n']
    (OUT/'样题与标注依据.md').write_text('\n'.join(doc)+'\n')
    (OUT/'README.md').write_text(
        '# Kev 续训 v3：七类方案的审阅包\n\n'
        '已生成四类新样题68条情境，共'+str(coverage['questions'])+'道子题；保留三类原数据，未启动训练。\n\n'
        '| 新生成类别 | 情境数 | 核心修正 |\n|---|---:|---|\n'
        '| 概率 | 12 | 双向条件化、贝叶斯、交并补、比较平局、带符号期望收益；choice/score/noul |\n'
        '| 信息不足 | 28 | 七种场景各四种信息状态；7条真正无法判断，7条虽缺字段仍可判断 |\n'
        '| 多跳 | 12 | 最近有权祖先、依赖传播方向、控股链、可用性和权限共同约束 |\n'
        '| 长政策 | 16 | 11条正赔付、5条拒赔；限额/子限额/免赔额顺序、例外和日期边界 |\n\n'
        '原样保留：工具路由900、时间/数值800、提示注入600条训练记录；development/test各保留300条。'
        '文件在retained/，与v2中相应记录逐字节一致。\n\n'
        '阅读：先看“修正说明.md”，再看“样题与标注依据.md”；可直接解析的候选在new_four_families.review.jsonl。'
        'manifest.json记录来源哈希、隔离方案和合并状态，coverage.json记录落盘检查。\n\n'
        '**这还不是可直接续训的完整新版本。** 68条是用于检查出题和打标的少量样题；'
        '没有把它们直接拼到2300条保留数据后面，以免四个修正类别被稀释。'
        '待审阅后再确定扩充量及合并采样权重。所有同源对照题当前统一置于review，未冒充独立dev/test。\n\n'
        '设计看过官方hard-v1错误，所以该旧测试集后续只能称已知诊断集。精确文本无重合不等于语义独立。'
        '本次没有第二个模型独立审题；检查为作者复核、手工参考值和程序校验。'
        '长政策有实质性不同条款，但仍共享一个合同骨架；扩充时须增加合同和场景结构，不能只换数字。\n\n'
        '复现：在仓库根目录运行 `python3 tools/build_targeted_v3_review.py`。\n')
    print(json.dumps({'output':str(OUT),'coverage':coverage,'retained':retained},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
