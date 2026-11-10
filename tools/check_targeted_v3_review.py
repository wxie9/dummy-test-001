#!/usr/bin/env python3
"""Check real Kev materialization and recompute high-risk labels from visible text.

This checker deliberately does not import the builder or its latent facts.
The parser only supports this pilot's authored language, not arbitrary policies.
"""
import copy
import hashlib
import json
import re
import sys
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/kev_training_eval_20261026/targeted_v3_review_20261029'
if sys.version_info < (3,10):
    raise SystemExit('Kev requires Python >= 3.10. Use the existing bundled Python runtime; see 修正说明.md.')
sys.path.insert(0,str(ROOT/'third_party/kev-source-20261025'))
from kev.data import api_request, materialize


def picked(r,key):
    q=r['questions'][key]
    return q['criteria'][q['label']]


def money(text):
    return int(Decimal(text.replace('$','').replace(',',''))*100)


def money_text(cents):
    return f'${cents/100:,.2f}'


def visible_ev(r):
    values={}
    for name,cost,outcomes in re.findall(r'Project ([A-Z]): upfront cost \$(\d+); ([^\n]+)',r['state']):
        terms=re.findall(r'([\d.]+)% probability: (gain|lose) \$(\d+)',outcomes)
        assert sum(Fraction(p)/100 for p,_,_ in terms)==1
        values[name]=sum(Fraction(p)/100*int(v)*(1 if sign=='gain' else -1) for p,sign,v in terms)-int(cost)
    assert len(values)>=2
    ordered=sorted(values,key=values.get,reverse=True)
    assert values[ordered[0]]>values[ordered[1]]
    assert picked(r,'project')=='Project '+ordered[0]
    asked=re.search(r'project ([A-Z])',r['questions']['expected_net']['instructions'])[1]
    assert picked(r,'expected_net')==f'${float(values[asked]):.2f}'


def visible_policy(r):
    policy,claim=r['state'].split('CLAIM RECORD\n')
    sections=dict(re.findall(r'(\d\. [^\n]+)\n(.*?)(?=\n\n\d\. |\n\n$|\Z)',policy,re.S))
    # Resolve the event from the claim, never from latent _meta.benefit.
    if 'signage was broken' in claim:
        section=sections['5. Venue property'];benefit='venue';category='signage'
    elif 'internal electrical failure' in claim:
        section=sections['3. Mechanical equipment'];benefit='mechanical'
        category='battery' if 'battery module' in claim else 'projector'
    else:
        section=sections['2. Imaging equipment'];benefit='imaging'
        category='recorder' if 'audio recorder' in claim else 'camera'
    loss=money(re.search(r'Gross eligible loss: (\$[\d,.]+)\.',claim)[1])
    cap=money(re.search(r'limit (?:is|would be) (\$[\d,]+)',section)[1])
    fee=money(re.search(r'(?:deductible is|with a) (\$[\d,]+)',section)[1])
    submatch=re.search(r'(\$[\d,]+) (?:(?:category|signage) )?sublimit',section)
    sub=money(submatch[1]) if category in ('battery','recorder','signage') else 10**12
    inception=date.fromisoformat(re.search(r'effective (\d{4}-\d{2}-\d{2})',policy)[1])
    incident=date.fromisoformat(re.search(r'Incident: (\d{4}-\d{2}-\d{2})',claim)[1])
    report=date.fromisoformat(re.search(r'Report: (\d{4}-\d{2}-\d{2})',claim)[1])
    waiting=int(re.search(r'waiting period is (\d+) elapsed',section)[1]) if benefit=='mechanical' else 0
    delay_limit=int(re.search(r'no more than (\d+) elapsed calendar days',policy)[1])
    if benefit=='venue':
        assert 'venue is not purchased' in policy
        amount=0;reason='Deny: the applicable benefit was not purchased'
    elif (incident-inception).days<waiting:
        amount=0;reason='Deny: the incident is inside the waiting period'
    elif benefit=='mechanical' and int(re.search(r'Operating hours at incident: (\d+)',claim)[1])>int(re.search(r'Usage strictly above ([\d,]+)',section)[1].replace(',','')):
        amount=0;reason='Deny: usage exceeds the allowed maximum'
    elif 'stolen from an unattended public' in claim and not('inside a locked cabinet;' in claim and 'photographs document forced entry' in claim):
        amount=0;reason='Deny: unattended public theft exclusion applies without its exception'
    elif (report-incident).days>delay_limit:
        amount=0;reason='Deny: the report is late'
    else:
        before='Subtract the benefit deductible once from gross eligible loss' in policy
        gross_or_net=max(0,loss-fee) if before else loss
        ceiling=min(cap,sub)
        amount=min(gross_or_net,ceiling) if before else max(0,min(gross_or_net,ceiling)-fee)
        reason=('Pay: eligible loss, adjusted by the deductible, determines the payment' if gross_or_net<=ceiling else
                'Pay: the item category sublimit binds under the stated arithmetic' if sub<=cap else
                'Pay: the benefit limit binds under the stated arithmetic')
    assert picked(r,'amount')==money_text(amount),(picked(r,'amount'),money_text(amount))
    assert picked(r,'reason')==reason


def rejects(mutated,check):
    try:check(mutated)
    except AssertionError:return
    raise AssertionError('visible-text checker failed to catch injected mismatch')


def main():
    rows=[json.loads(x) for x in (OUT/'new_four_families.review.jsonl').read_text().splitlines()]
    evs=[];policies=[]
    for r in rows:
        req=api_request(r)
        assert set(req)=={'state','questions'}
        assert all(set(q)<= {'type','instructions','criteria'} for q in req['questions'].values())
        rec=materialize(r)
        assert rec['state']==r['state']
        assert len(rec['questions'])==len(r['questions'])
        assert all(0<=q['label']<len(q['options']) for q in rec['questions'])
        if 'expected_net' in r['questions']:
            visible_ev(r);evs.append(r)
        if 'amount' in r['questions']:
            visible_policy(r);policies.append(r)
    # Demonstrate the checker detects the exact signed-loss failure class seen
    # in v2, and an order-of-deductible rendering mismatch.
    ev_bad=copy.deepcopy(evs[0]);ev_bad['state']=ev_bad['state'].replace('lose $80','gain $80')
    rejects(ev_bad,visible_ev)
    order_bad=copy.deepcopy(policies[0])
    order_bad['state']=order_bad['state'].replace(
        'Apply limits to the gross eligible loss first: take the smallest of loss, benefit limit and any applicable category sublimit; then subtract the benefit deductible once, flooring at zero.',
        'Subtract the benefit deductible once from gross eligible loss, flooring at zero; then apply the benefit limit and any applicable category sublimit to that net amount.')
    rejects(order_bad,visible_policy)
    report={
        'official_kev_materialize_contexts':len(rows),
        'official_kev_materialize_questions':sum(len(r['questions']) for r in rows),
        'metadata_and_labels_excluded_from_input':True,
        'visible_text_recomputed_ev_contexts':len(evs),
        'visible_text_recomputed_policy_contexts':len(policies),
        'deliberate_sign_error_rejected':True,'deliberate_deductible_order_error_rejected':True,
        'independent_external_reviewer':False,
        'limits':'Same-author parser checks only the specified high-risk renderings. Other pilot scenarios receive authored reference checks and manual semantic review; no general natural-language proof is claimed.',
        'data_sha256':hashlib.sha256((OUT/'new_four_families.review.jsonl').read_bytes()).hexdigest(),
    }
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
