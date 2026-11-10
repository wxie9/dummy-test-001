#!/usr/bin/env python3
"""Recompute rule labels from rendered text, without reading latent fact values."""
import json,re,sys
from datetime import date
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/kev-source-20261025'))
from kev.api import render
from kev.data import materialize
OUT=ROOT/'artifacts/kev_training_eval_20261026/targeted_v4_20261030'

def find(pattern,s):return re.search(pattern,s,re.S)[1]
def money(s):return Decimal(s.replace('$','').replace(',','').rstrip('.'))
def gold(r,q):return r['questions'][q]['criteria'][r['questions'][q]['label']]
def dt(s):return date.fromisoformat(s)

def missing(r):
    s=render(r['state']);kind=r['_meta']['subtype'].split('__')[0]
    # Each possible value below is justified by an explicit visible bound. If
    # all admissible completions agree, missing information is nondecisive.
    if kind=='return':
        limit=int(find(r'no more than (\d+) elapsed',s));request=dt(find(r'Return requested: ([\d-]+)',s));order=dt(find(r'Order date: ([\d-]+)',s))
        delivered=re.search(r'Delivered: ([\d-]+)',s)
        days=[(request-dt(delivered[1])).days] if delivered else [0,(request-order).days]
        decisions={v<=limit for v in days}
    elif kind=='approval':
        amount=int(find(r'Amount: \$(\d+)',s));limit=int(find(r'Payments below \$(\d+)',s))
        level=re.search(r'\w+ has authority level (\d)',s)
        levels=[int(level[1])] if level else [1,2,3]
        decisions={amount<limit or v>=2 for v in levels}
    elif kind=='tenure':
        limit=int(find(r'at least (\d+) elapsed',s));application=dt(find(r'employment by ([\d-]+)',s));transfer=dt(find(r'transferred to the Support team on ([\d-]+)',s))
        hired=re.search(r'Company hire date: ([\d-]+)',s)
        days=[(application-dt(hired[1])).days] if hired else [(application-transfer).days,max(limit+1,(application-transfer).days)]
        decisions={v>=limit for v in days}
    elif kind=='shipping':
        subtotal=int(find(r'Merchandise subtotal: \$(\d+)',s));limit=int(find(r'at least \$(\d+)',s));maximum=int(find(r'between \$0 and \$(\d+)',s))
        discount=re.search(r'Merchandise discount: \$(\d+)',s)
        values=[int(discount[1])] if discount else [0,maximum]
        decisions={subtotal-v>=limit for v in values}
    elif kind=='overtime':
        limit=int(find(r'strictly exceed (\d+)',s));maximum=int(find(r'each between 0 and (\d+) hours',s));first=json.loads(find(r'Thursday hours: (\[[^\]]+\])',s))
        friday=re.search(r'Friday hours: (\d+)',s);values=[int(friday[1])] if friday else [0,maximum]
        decisions={sum(first)+v>limit for v in values}
    elif kind=='warranty':
        expiry=dt(find(r'expires on ([\d-]+)',s));claim=dt(find(r'Claim received: ([\d-]+)',s))
        cause=re.search(r'confirmed cause: (manufacturing defect|accidental damage)',s)
        values=[cause[1]] if cause else ['manufacturing defect','accidental damage']
        decisions={claim<=expiry and v=='manufacturing defect' for v in values}
    else:
        price=int(find(r'Our price: \$(\d+)',s));competitor=int(find(r'Competitor price: \$(\d+)',s));limit=int(find(r'at most (\d+)%',s))
        stock=re.search(r'Competitor inventory: (in stock|out of stock)',s)
        values=[stock[1]=='in stock'] if stock else [True,False]
        decisions={v and competitor<price and 100*(price-competitor)<=limit*price for v in values}
    answer='Cannot determine from the information given' if len(decisions)>1 else 'The requirement is satisfied' if True in decisions else 'The requirement is not satisfied'
    assert gold(r,'decision')==answer,(r['_meta']['id'],gold(r,'decision'),answer)
    return decisions

def policy(r):
    s=r['state'];text,claim=s.split('INCIDENT FILE\n')
    event=find(r'Event: ([^.]+)\.',claim);item=find(r'Claimed item: ([^.]+)\.',claim)
    sections=re.findall(r'BENEFIT (B\d): ([^\n]+)\n(.*?)(?=\n\n|\Z)',text,re.S)
    matching=[(code,body) for code,title,body in sections if title==event]
    assert len(matching)==1
    code,b=matching[0]
    cap=money(find(r'Its limit is (\$[\d.]+)',b));fee=money(find(r'deductible (\$[\d.]+)',b));sub=money(find(r'part sublimit is (\$[\d.]+)',b))
    part=find(r'applies only when the claimed item is the ([^.]+)\.',b)
    waiting=int(find(r'Waiting period: (\d+) elapsed',b));usage_max=int(find(r'Usage above (\d+) hours',b))
    loss=money(find(r'Eligible loss: (\$[\d.]+)',claim));usage=int(find(r'Usage at incident: (\d+)',claim))
    inception=dt(find(r'Inception: ([\d-]+)',text));incident=dt(find(r'Incident: ([\d-]+)',claim));reported=dt(find(r'Reported: ([\d-]+)',claim))
    notice=int(find(r'within (\d+) elapsed calendar days',text))
    purchased=find(code+r': (purchased|not purchased)',text)=='purchased'
    unsafe=find(r'Storage: (unsafe|normal)',claim)=='unsafe';exception='Waiver: signed before incident.' in claim
    if not purchased:reason='not purchased'
    elif (incident-inception).days<waiting:reason='waiting period'
    elif usage>usage_max:reason='usage maximum'
    elif unsafe and not exception:reason='unsafe storage'
    elif (reported-incident).days>notice:reason='late report'
    else:reason=None
    if reason:amount=Decimal(0)
    else:
        before='Subtract the deductible from eligible loss first' in text
        entering=max(0,loss-fee) if before else loss;ceiling=min(cap,sub) if item==part else cap
        amount=min(entering,ceiling) if before else max(0,min(entering,ceiling)-fee)
        reason='loss based' if entering<=ceiling else 'part ceiling' if item==part else 'benefit ceiling'
    assert gold(r,'amount')==f'${amount:.2f}'
    assert gold(r,'reason')==reason

def main():
    counts={}
    for family,check in [('insufficient',missing),('policy',policy)]:
        path=OUT/'components'/f'{family}.candidate.jsonl';rows=[json.loads(l) for l in path.read_text().splitlines()]
        for r in rows:materialize(r);check(r)
        counts[family]=len(rows)
    (OUT/'rules_validation.json').write_text(json.dumps({'visible_text_recomputed':counts,'independent_external_reviewer':False,'scope':'Same-author second implementation parses visible numbers, dates, rules and case facts; does not read latent fact values.'},indent=2)+'\n')
    print(counts)

if __name__=='__main__':main()
