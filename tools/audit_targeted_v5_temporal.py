#!/usr/bin/env python3
"""Read visible retained temporal problems and audit endpoint ambiguity."""
import json
import re
from datetime import datetime, timezone
from fractions import Fraction as F
from zoneinfo import ZoneInfo
from build_targeted_v5 import OUT

def date_value(s):
    for fmt in ['%B %d, %Y','%d %B %Y','%Y-%m-%d']:
        try:return datetime.strptime(s,fmt).date()
        except ValueError:pass
    raise ValueError(s)

def round_cents(v):return (v.numerator*2+v.denominator)//(2*v.denominator)

def audit(rows):
    problems=[];zones=[]
    for r in rows:
        if r['_meta']['family']!='temporal':continue
        s=r['state'];q=r['questions']['decision'];answer=q['criteria'][q['label']]
        if r['_meta']['subtype']=='prorata':
            match=re.fullmatch(r'A subscription costing \$([\d,.]+) runs from (.*?) through (.*?)\. It was cancelled on (.*?)\. The cancellation day counts as used\. Refund unused days pro rata, rounded to the nearest cent\. What is the refund\?',s)
            assert match
            cents=F(match[1].replace(',',''))*100;assert cents.denominator==1
            start,end,cancel=map(date_value,match.group(2,3,4))
            used=(cancel-start).days+1;span=(end-start).days
            exclusive=round_cents(cents*F(span-used,span))
            inclusive=round_cents(cents*F(span+1-used,span+1))
            gold_cents=int(F(answer.replace('$','').replace(',',''))*100)
            assert gold_cents==exclusive
            problems.append({'id':r['_meta']['id'],'state':s,'label':answer,'end_excluded_cents':exclusive,'end_included_cents':inclusive,
                'same_rounded_answer':exclusive==inclusive,'issue':'through does not explicitly specify the exclusive endpoint assumed by the label'})
        elif r['_meta']['subtype']=='timezone':
            m=re.search(r'at ([\d-]+ [\d:]+) in ([\w/]+)\. Convert it to local time in ([\w/]+)',s);assert m
            local=datetime.strptime(m[1],'%Y-%m-%d %H:%M');zone=ZoneInfo(m[2])
            candidates=[]
            for fold in (0,1):
                aware=local.replace(tzinfo=zone,fold=fold)
                roundtrip=aware.astimezone(timezone.utc).astimezone(zone)
                if roundtrip.replace(tzinfo=None)==local:candidates.append(aware.astimezone(ZoneInfo(m[3])).strftime('%Y-%m-%d %H:%M'))
            if len(set(candidates))!=1:zones.append({'id':r['_meta']['id'],'state':s,'possible_destination_times':sorted(set(candidates))})
    return {'prorata_endpoint_ambiguities':problems,'timezone_ambiguous_or_nonexistent':zones}

def main():
    result={}
    for split in ['train','development']:
        rows=[json.loads(l) for l in (OUT/(split+'.jsonl')).read_text().splitlines()]
        result[split]=audit(rows)
    result['status']='read-only audit; frozen v5 data unchanged; clarification requested because user asked to preserve the original three families'
    result['causality']='Does not establish that this wording caused the observed accuracy regression.'
    (OUT/'retained_temporal_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print({s:{k:len(v) for k,v in r.items()} for s,r in result.items() if isinstance(r,dict)})

if __name__=='__main__':main()
