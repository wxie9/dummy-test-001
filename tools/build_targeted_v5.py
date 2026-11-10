#!/usr/bin/env python3
"""V5: matched missing-fact/policy pairs, plausible probability distractors,
and partial-candidate graph decisions. Preserve the original three families.
Never imports a benchmark generator or uses test labels to create records.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter
from datetime import date, timedelta
from fractions import Fraction as F
from pathlib import Path
import sys

from build_targeted_v4_components import ROOT, dump, choice, cash, percent, probability, graph, record
from build_targeted_v4_rules import insufficient, contract, ANS
from check_targeted_v4_rules import missing, policy, materialize, render, gold
from check_targeted_v4_numeric import probability as check_probability, graph as check_graph

VERSION = 'targeted-v5-20261030'
OUT = ROOT / 'artifacts/kev_training_eval_20261026/targeted_v5_20261030'
OLD = OUT.with_name('targeted_v4_20261030')
SCENARIOS = ['return', 'approval', 'tenure', 'shipping', 'overtime', 'warranty', 'price_match']
BEFORE = 'Subtract the deductible from eligible loss first, flooring at zero. Apply the benefit limit and any applicable part sublimit to the remaining loss.'
AFTER = 'First cap eligible loss by the benefit limit and any applicable part sublimit. Subtract the deductible from that capped amount once, flooring at zero.'
NONE = 'None of the listed candidates'

def digest(s):
    return hashlib.sha256(' '.join(render(s).casefold().split()).encode()).hexdigest()

def transform_state(r, fn):
    s = r['state']
    r['state'] = {k: fn(v) for k, v in s.items()} if isinstance(s, dict) else fn(s)

def append_case(r, fact):
    s = r['state']
    if isinstance(s, dict):
        s['case'] += fact
    elif '\nAPPLICABLE RULE\n' in s:
        r['state'] = s.replace('\nAPPLICABLE RULE\n', fact + '\nAPPLICABLE RULE\n')
    else:
        r['state'] += fact

def with_identity(r, split, index, pair=None):
    m = r['_meta']; m['id'] = f'{VERSION}/{m["family"]}/{split}/{index:06d}'
    m['source'] = VERSION + '_' + m['family']; m['split'] = split
    m['group_id'] = pair or m['id']; m['text_sha256'] = digest(r['state'])
    for q in r['questions'].values():
        q['src'] = m['source']
    return r

def missing_pair(index, scenario, nondeciding, rng):
    # Generate the missing record first; complete its *same* case with one
    # feasible witness. No other condition or option ordering changes.
    absent = insufficient(index, scenario, 'nondeciding' if nondeciding else 'unknown', rng)
    transform_state(absent, lambda s: s.replace('The decisive field, if not listed,', 'An unlisted field'))
    f = absent['_meta']['facts']; w = f['witnesses'][index % 2]
    s = render(absent['state'])
    if scenario == 'return':
        when = date.fromisoformat(re.search(r'Return requested: ([\d-]+)', s)[1]) - timedelta(days=w['delivery_elapsed_days'])
        fact = f' Delivered: {when}.'
    elif scenario == 'approval':
        name = re.search(r'Actual approver: (\w+)', s)[1]
        fact = f' {name} has authority level {w["actual_approver_level"]}.'
    elif scenario == 'tenure':
        when = date.fromisoformat(re.search(r'employment by ([\d-]+)', s)[1]) - timedelta(days=w['company_tenure_days'])
        fact = f' Company hire date: {when}.'
    elif scenario == 'shipping': fact = f' Merchandise discount: ${w["discount"]}.'
    elif scenario == 'overtime': fact = f' Friday hours: {w["friday_hours"]}.'
    elif scenario == 'warranty': fact = f' Technician confirmed cause: {w["cause"]}.'
    else: fact = ' Competitor inventory: ' + ('in stock.' if w['competitor_in_stock'] else 'out of stock.')
    complete = copy.deepcopy(absent); append_case(complete, fact)
    q = complete['questions']['decision']
    q['label'] = next(k for k,v in q['criteria'].items() if v == ANS[w['eligible']])
    complete['_meta']['facts'] = {'scenario':scenario, 'variant':'yes' if w['eligible'] else 'no', 'witnesses':[w]}
    complete['_meta']['subtype'] = scenario + '__complete'
    for r, role in [(complete, 'complete'), (absent, 'missing_nondeciding' if nondeciding else 'missing_deciding')]:
        r['_meta']['pair_role'] = role
        r['_meta']['pair_fact'] = fact.strip()
        r['_meta']['review_zh'] = '同一案例只增删一个事实；' + ('缺失不改变结论。' if nondeciding else '缺失后存在结论相反的合法补全。')
        missing(r)
    # Remove the added fact and obtain exactly the original rendered state.
    reverted = copy.deepcopy(complete); transform_state(reverted, lambda s:s.replace(fact, ''))
    assert reverted['state'] == absent['state']
    assert (gold(complete, 'decision') == gold(absent, 'decision')) == nondeciding
    return [complete, absent]

def policy_labels(r, rng):
    f = r['_meta']['facts']; b = f['benefits'][f['selected']]
    why = ('not purchased' if not b['purchased'] else 'waiting period' if f['elapsed'] < b['waiting'] else
           'usage maximum' if f['use'] > b['usage_limit'] else 'unsafe storage' if f['unsafe'] and not f['exception'] else
           'late report' if f['delay'] > f['notice'] else None)
    entering = max(0, f['loss']-b['fee']) if f['before'] else f['loss']
    ceiling = min(b['cap'], b['sub']) if f['ispart'] else b['cap']
    amount = min(entering, ceiling) if f['before'] else max(0, min(entering, ceiling)-b['fee'])
    if why: amount = 0
    else: why = 'loss based' if entering <= ceiling else 'part ceiling' if f['ispart'] else 'benefit ceiling'
    # Include both operation orders, gross loss and nearby numerical mistakes.
    mistakes = [cash(0), cash(f['loss']), cash(b['cap']), cash(b['sub']), cash(max(0, amount-b['fee'])), cash(amount+b['fee'])]
    r['questions']['amount'] = choice(rng, 'What payment is due?', cash(amount), mistakes)
    reasons = ['loss based','part ceiling','benefit ceiling','not purchased','waiting period','usage maximum','unsafe storage','late report']
    r['questions']['reason'] = choice(rng, 'Select the controlling reason under the policy definitions.', why, reasons)
    f.update(expected_payment=amount, expected_reason=why)
    r['_meta']['review_zh'] = f'可见条款复算：赔付{cash(amount)}；控制理由{why}；先扣免赔{f["before"]}。'
    policy(r)

def policy_pair(index, kind, target, rng):
    # Domain and operation order must not be determined by target label.
    first = contract(rng.randrange(1000000), target, rng); second = copy.deepcopy(first)
    f = second['_meta']['facts']; b = f['benefits'][f['selected']]
    if kind == 'order':
        old, new = (BEFORE, AFTER) if f['before'] else (AFTER, BEFORE)
        assert second['state'].count(old) == 1
        second['state'] = second['state'].replace(old, new); f['before'] = not f['before']
    elif kind == 'boundary':
        if target == 'not_purchased':
            second['state'] = second['state'].replace(b['code']+': not purchased', b['code']+': purchased'); b['purchased'] = True
        elif target == 'waiting':
            # Change inception alone; report delay stays fixed.
            old = re.search(r'Inception: ([\d-]+)', second['state'])[1]
            new = str(date.fromisoformat(old)-timedelta(days=1))
            second['state'] = second['state'].replace('Inception: '+old, 'Inception: '+new); f['elapsed'] += 1
        elif target == 'usage':
            second['state'] = second['state'].replace(f'Usage at incident: {f["use"]} hours', f'Usage at incident: {b["usage_limit"]} hours'); f['use'] = b['usage_limit']
        elif target == 'unsafe':
            second['state'] = second['state'].replace('Waiver: none.', 'Waiver: signed before incident.'); f['exception'] = True
        elif target == 'late':
            old = re.search(r'Reported: ([\d-]+)', second['state'])[1]
            new = str(date.fromisoformat(old)-timedelta(days=1))
            second['state'] = second['state'].replace('Reported: '+old, 'Reported: '+new); f['delay'] -= 1
    else:
        # Add a second exclusion; the documented priority must select one reason.
        if target == 'not_purchased':
            second['state'] = second['state'].replace('Storage: normal.', 'Storage: unsafe.'); f['unsafe'] = True
        else:
            second['state'] = second['state'].replace(b['code']+': purchased', b['code']+': not purchased'); b['purchased'] = False
    for r in (first, second):
        r['_meta']['pair_kind'] = kind
        policy_labels(r, rng)
    assert first['state'] != second['state']
    if kind == 'boundary': assert gold(first, 'amount') == '$0.00' and gold(second, 'amount') != '$0.00'
    return [first, second]

def probability_hard(index, kind, rng):
    if kind == 'compare':
        p,q = [F(rng.choice([20,25,40,50,60,75,80]),100) for _ in range(2)]
        op = rng.choice(['AND','OR']); first = p*q if op=='AND' else p+q-p*q
        difference = [F(-1,100),F(0),F(1,100)][index%3]
        second = first+difference
        assert 0<=second<=1 and F(percent(second)[:-1])/100==second
        state=f'A and B are independent, with probabilities {percent(p)} and {percent(q)}. Event X means '+('both A and B happen' if op=='AND' else 'at least one of A and B happens')+f'. Event Y has probability {percent(second)}. Compare marginal probabilities only; dependence between X and Y is irrelevant.'
        labels=['X is more likely','They have equal probabilities','Y is more likely']
        r=record('probability',index,state,{'decision':choice(rng,'Which statement is correct?',labels[index%3],labels)},
            {'p':str(p),'q':str(q),'op':op,'second':str(second)},kind,f'X={percent(first)}; Y={percent(second)}。')
    else:
        r = probability(index, kind, rng)
    if r is None: return None
    f = r['_meta']['facts']
    for key,q in list(r['questions'].items()):
        if q['type'] != 'choice' or not all(re.fullmatch(r'[\d.]+%', x) for x in q['criteria'].values()): continue
        answer = gold(r, key); p = F(answer[:-1])/100
        values = [1-p]
        if kind == 'table':
            a,b,c,d = f['counts']; values += [F(a,a+b), F(a,a+c), F(a,a+b+c+d), F(c,a+c), F(b,a+b)]
        elif kind == 'bayes':
            b,h,z = (F(f[x],100) for x in ['prevalence','sensitivity','false_positive'])
            values += [b, h, b*h, 1-z, b*h+(1-b)*z]
        else:
            ps = [F(x,100) for x in f['probabilities']]; allp = F(1); none = F(1)
            for x in ps: allp *= x; none *= 1-x
            values += [allp, 1-allp, none, 1-none, sum(ps)/len(ps), min(ps)]
        values += [max(F(0), p-F(13,1000)), min(F(1), p+F(17,1000)), max(F(0), p-F(29,1000))]
        distractors = list(dict.fromkeys(percent(v) for v in values if percent(v) != answer))
        rng.shuffle(distractors); q2 = choice(rng, q['instructions'], answer, distractors[:4])
        assert len(q2['criteria']) == 5
        r['questions'][key] = q2
    check_probability(r)
    return r

def graph_decision(index, kind, rng):
    if kind == 'ownership':
        r = graph(index, kind, rng); check_graph(r); return r
    names = rng.sample(['Amber','Brook','Cove','Dune','Echo','Fern','Glade','Haven','Islet','Jade','Knoll','Lumen','Mesa','Nexus','Opal','Peak','Ridge','Shore','Vale','Willow','Zephyr'], 13)
    path = names[:rng.randint(4,8)]; noise = names[8:]
    if kind == 'dependency_candidates':
        down = path[-1]; edges = [(a,b,True) for a,b in zip(path,path[1:])]
        edges += [(noise[0],down,False), (down,noise[1],True), (noise[2],noise[3],True)]
        # One branching dependent and one soft link into the hard chain.
        edges += [(noise[4], path[1], True)]
        affected = set(path+[noise[4]])
        choose_none = index % 3 == 0
        unaffected = [n for n in names if n not in affected]
        candidates = rng.sample(unaffected,3)
        if not choose_none: candidates[rng.randrange(3)] = rng.choice(path[:-1]+[noise[4]])
        rng.shuffle(edges)
        state = 'DEPENDENCY OPERATIONS MEMO\nA hard prerequisite failure disables its consumer, repeatedly until stable. A soft prerequisite failure has no effect on its consumer. No other propagation rule exists.\n'
        state += '\n'.join(f'{a} uses {b} as a {"hard" if hard else "soft"} prerequisite.' for a,b,hard in edges)
        state += f'\nOnly {down} is initially failed. All other units initially function.'
        selected = [n for n in candidates if n in affected]; assert len(selected)<=1
        answer = selected[0] if selected else NONE
        q = choice(rng, 'Which of the listed candidates is disabled after all failure propagation?', answer, candidates+[NONE])
        f = {'edges':edges,'initial':down,'affected':sorted(affected),'candidates':candidates}
    else:
        titles = ['Associate','Specialist','Lead','Principal','Head','Executive']
        threshold = rng.randint(2,4); level = {n:rng.randrange(len(titles)) for n in names}
        answer_position = rng.randint(2,len(path)-1)
        for n in path[1:answer_position]: level[n]=rng.randrange(threshold)
        level[path[answer_position]]=rng.randint(threshold,len(titles)-1)
        links=list(zip(path,path[1:]))+[(noise[0],noise[1]),(noise[2],path[1])];rng.shuffle(links)
        lines=[f'{a} has supervisor {b}.' for a,b in links]+[f'{n} holds rank {titles[level[n]]}.' for n in names]
        rng.shuffle(lines)
        state='AUTHORIZATION DIRECTORY\nRanks in increasing authority: '+', '.join(titles)+f'. A request is routed from its origin upward to the first supervisor with rank {titles[threshold]} or higher; the origin cannot approve its own request.\n'+'\n'.join(lines)+f'\nRequest origin: {path[0]}.'
        answer=path[answer_position]
        q=choice(rng,'Who must approve this request?',answer,path[1:]+noise[:2])
        f={'path':path,'links':links,'ranks':level,'threshold':threshold}
    r=record('multihop',index,state,{'decision':q},f,kind,'根据可见边和条件逐跳求解；不依赖同名节点的位置。')
    check_graph_decision(r)
    return r

def check_graph_decision(r):
    s=r['state'];kind=r['_meta']['subtype']
    if kind=='ownership': return check_graph(r)
    if kind=='dependency_candidates':
        edges=re.findall(r'(\w+) uses (\w+) as a (hard|soft) prerequisite\.',s)
        failed=re.search(r'Only (\w+) is initially failed',s)[1];affected={failed}
        while True:
            new=affected|{a for a,b,t in edges if t=='hard' and b in affected}
            if new==affected:break
            affected=new
        possible=[v for v in r['questions']['decision']['criteria'].values() if v in affected]
        assert len(possible)<=1
        answer=possible[0] if possible else NONE
    else:
        ranks=re.search(r'Ranks in increasing authority: ([^.]+)\.',s)[1].split(', ')
        required=re.search(r'with rank (\w+) or higher',s)[1]
        links=dict(re.findall(r'(\w+) has supervisor (\w+)\.',s))
        attrs=dict(re.findall(r'(\w+) holds rank (\w+)\.',s))
        node=re.search(r'Request origin: (\w+)',s)[1];visited=set()
        while node in links:
            node=links[node];assert node not in visited;visited.add(node)
            if ranks.index(attrs[node])>=ranks.index(required):break
        else:raise AssertionError('No approver')
        answer=node
    assert gold(r,'decision')==answer

def make_split(split, counts, seen, frozen):
    rows=[];pair_index=0
    def admit(items, pair=False):
        nonlocal pair_index
        hashes=[digest(r['state']) for r in items]
        if len(set(hashes))!=len(items) or any(h in seen or h in frozen for h in hashes):return False
        group=f'{VERSION}/{split}/pair{pair_index:05d}' if pair else None
        for r in items:
            with_identity(r,split,len(rows),group);materialize(r);seen.add(digest(r['state']));rows.append(r)
        if pair:pair_index+=1
        return True
    for scene in SCENARIOS:
        for non,n in [(False,counts['deciding_pairs']),(True,counts['nondeciding_pairs'])]:
            made=0;attempt=0
            while made<n:
                attempt+=1;assert attempt<2000
                seed=f'{VERSION}/{split}/{scene}/{non}/{attempt}'
                if admit(missing_pair(made,scene,non,random.Random(seed)),True):made+=1
    deny=['not_purchased','waiting','usage','unsafe','late']
    for kind,n,targets in [('order',counts['policy_order'],['pay_loss','pay_limit','pay_sublimit']),('boundary',counts['policy_boundary'],deny),('multiple_denial',counts['policy_multiple'],deny)]:
        for i in range(n):
            for attempt in range(2000):
                rs=policy_pair(i,kind,targets[i%len(targets)],random.Random(f'{VERSION}/{split}/{kind}/{i}/{attempt}'))
                if admit(rs,True):break
            else:raise AssertionError('Policy uniqueness exhausted')
    for kind,n in counts['probability'].items():
        made=0;attempt=0
        while made<n:
            attempt+=1;assert attempt<10000
            r=probability_hard(made,kind,random.Random(f'{VERSION}/{split}/{kind}/{attempt}'))
            if r is not None and admit([r]):made+=1
    for kind,n in counts['graph'].items():
        made=0;attempt=0
        while made<n:
            attempt+=1;assert attempt<10000
            r=graph_decision(made,kind,random.Random(f'{VERSION}/{split}/{kind}/{attempt}'))
            if admit([r]):made+=1
    # Original three family records retained byte-for-byte as JSON objects.
    old=[json.loads(l) for l in (OLD/(split+'.jsonl')).read_text().splitlines()]
    for r in old:
        if r['_meta']['family'] in ['tool_routing','temporal','injection']:
            h=digest(r['state']);assert h not in seen and h not in frozen
            seen.add(h);materialize(r);rows.append(r)
    random.Random(VERSION+split).shuffle(rows)
    return rows

def main():
    OUT.mkdir(exist_ok=True)
    frozen={digest(json.loads(l)['state']) for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl') for l in p.read_text().splitlines()}
    seen=set()
    train=make_split('train',{'deciding_pairs':16,'nondeciding_pairs':4,'policy_order':60,'policy_boundary':60,'policy_multiple':30,
        'probability':{'table':75,'bayes':60,'all':40,'any_fail':50,'any':25,'compare':40,'expected_value':60},
        'graph':{'dependency_candidates':90,'rank_escalation':90,'ownership':90}},seen,frozen)
    dev=make_split('development',{'deciding_pairs':4,'nondeciding_pairs':1,'policy_order':15,'policy_boundary':10,'policy_multiple':5,
        'probability':{'table':10,'bayes':10,'all':8,'any_fail':10,'any':6,'compare':6,'expected_value':10},
        'graph':{'dependency_candidates':20,'rank_escalation':20,'ownership':20}},seen,frozen)
    assert len(train)==1500 and len(dev)==340
    manifest={'version':VERSION,'status':'text_checked_tokenization_pending','files':{},'goal_achieved':False,'replay':6000,'init':'original pre-targeted stage3',
        'scope':'Same-author generators and separate visible-text recomputation; matched-pair groups kept within splits. Development shares generators and is not independent generalization evidence.',
        'checks':{'exact_state_overlap_train_dev':0,'exact_state_overlap_frozen_tests':0,'original_three_families_content_unchanged':True,'materialize_all':'passed','visible_text_recomputed_new_four':'passed'}}
    for split,rows in [('train',train),('development',dev)]:
        p=OUT/(split+'.jsonl');p.write_text(''.join(dump(r)+'\n' for r in rows))
        f=Counter(r['_meta']['family'] for r in rows)
        manifest['files'][split]={'contexts':len(rows),'questions':sum(len(r['questions']) for r in rows),'families':dict(f),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'insufficient_answers':dict(Counter(gold(r,'decision') for r in rows if r['_meta']['family']=='insufficient')),
            'policy_positive':sum(gold(r,'amount')!='$0.00' for r in rows if r['_meta']['family']=='policy')}
    groups=lambda rs:{r['_meta']['group_id'] for r in rs if r['_meta']['id'].startswith(VERSION)}
    assert not groups(train)&groups(dev)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
