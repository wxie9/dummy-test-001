#!/usr/bin/env python3
"""Describe numeric coverage and existing inspected-test errors; no generation."""
import hashlib
import json
import statistics
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
from build_kev_probability_coverage_candidate import OUT, probability_of

ROOT=Path(__file__).resolve().parents[1]
V5=OUT.with_name('targeted_v5_20261030')


def describe(values):
    return {'n':len(values),'min':min(values),'median':statistics.median(values),'max':max(values),
            'below_30':sum(v<30 for v in values)}


def measures(rows,reference=False):
    result=defaultdict(list)
    for r in rows:
        m=r['_meta'];f=m.get('facts',{})
        if reference:
            if m['source']!='hard_probability':continue
            kind=f['kind']
            if kind=='independent':
                kind=f['ask'];ps=list(map(F,f['ps']))
                result[kind+'/success_rate_pct'].extend(float(p*100) for p in ps)
                result[kind+'/answer_probability_pct'].append(float(probability_of(ps,kind)*100))
            elif kind=='ev':
                for project in f['projects'].values():
                    result['ev/absolute_payoff_dollars'].extend(abs(v) for _,v in project['outcomes'])
                    result['ev/upfront_cost_dollars'].append(project['cost'])
        else:
            if m.get('family')!='probability':continue
            kind=m['subtype']
            if kind in ['all','any','any_fail']:
                ps=[F(p,100) for p in f['probabilities']]
                result[kind+'/success_rate_pct'].extend(f['probabilities'])
                result[kind+'/answer_probability_pct'].append(float(probability_of(ps,kind)*100))
            elif kind=='expected_value':
                for project in f['projects'].values():
                    result['ev/absolute_payoff_dollars'].extend(abs(v) for v in project['values'])
                    result['ev/upfront_cost_dollars'].append(project['cost'])
    return {name:describe(values) for name,values in result.items()}


def main():
    paths={'v5_train':V5/'train.jsonl','candidate_train':OUT/'train.candidate.jsonl',
           'inspected_diagnostic':ROOT/'third_party/kev-source-20261025/evals/hard-v1/test.jsonl'}
    rows={name:[json.loads(l) for l in p.read_text().splitlines()] for name,p in paths.items()}
    report={'scope':'Post-hoc coverage audit of an already-inspected benchmark. Distribution mismatch motivates a broad-coverage candidate but does not prove causality or held-out improvement.',
            'hashes':{name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in paths.items()},
            'coverage':{name:measures(rs,name=='inspected_diagnostic') for name,rs in rows.items()}}
    records={r['_meta']['id']:r for r in rows['inspected_diagnostic'] if r['_meta']['source']=='hard_probability'}
    groups=defaultdict(list)
    for line in (V5/'paired-seven.jsonl').read_text().splitlines():
        p=json.loads(line)
        if p['source']!='hard_probability':continue
        f=records[p['id']]['_meta']['facts']
        if f['kind']!='independent':continue
        probability=probability_of(list(map(F,f['ps'])),f['ask'])
        band='below30' if probability<F(3,10) else '30to70' if probability<F(7,10) else '70plus'
        groups[(p['model'],f['ask'],band)].append(p)
    report['v5_independent_subgroups']=[{'model':m,'mechanism':k,'band':b,'contexts':len({p['id'] for p in ps}),
        'questions':len(ps),'before_correct':sum(p['before_ok'] for p in ps),'after_correct':sum(p['after_ok'] for p in ps)} for (m,k,b),ps in sorted(groups.items())]
    (OUT/'coverage_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for row in report['v5_independent_subgroups']:print(row)


if __name__=='__main__':main()
