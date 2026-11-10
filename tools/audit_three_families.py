"""Audit all three frozen hard-v1 families against paired local prediction snapshots.

No generation or training. Mechanism labels come from official record metadata;
these identify task requirements, not a model's unobserved internal failure cause.
"""
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'third_party/kev-source-20261025'
OUT = ROOT / 'artifacts/kev_training_eval_20261026/audit_three_families_20261029'
sys.path.insert(0, str(SOURCE))
from scripts.hard_v1_families import labels
from scripts.hard_v1_policy import solve, condition

def read_jsonl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def correct(r):
    return max(range(len(r['p'])), key=r['p'].__getitem__) == r['label']

def stats(rows, model):
    before = sum(r[model+'_before_ok'] for r in rows)
    after = sum(r[model+'_after_ok'] for r in rows)
    repaired = sum(not r[model+'_before_ok'] and r[model+'_after_ok'] for r in rows)
    broken = sum(r[model+'_before_ok'] and not r[model+'_after_ok'] for r in rows)
    return dict(n=len(rows), before=before, after=after, repaired=repaired, broken=broken,
                persistent_wrong=len(rows)-before-repaired)

def main():
    test_path = SOURCE / 'evals/hard-v1/test.jsonl'
    records = {r['_meta']['id']:r for r in read_jsonl(test_path)
               if r['_meta']['family'] in ('probability','ambiguous','long_policy')}
    snapshots = {}
    for name in ('q3_before','q3_after','q35_before','q35_after'):
        raw = json.loads((OUT/'raw'/f'{name}.json').read_text())
        snapshots[name] = {(r['id'],r['question']):r for r in raw}
        assert len(snapshots[name]) == len(raw), name
    result = []
    for rid, record in records.items():
        meta, f = record['_meta'], record['_meta']['facts']
        recomputed = labels(meta['family'], f, record['questions'])
        for qid, spec in record['questions'].items():
            assert recomputed[qid] == spec['label'], (rid,qid,'solver')
            mechanism = meta['subtype']
            if meta['family']=='probability':
                if mechanism in ('independent','table'): mechanism += ':'+f['ask']
                if mechanism=='compare': mechanism += ':'+f['a']['op']
            row = dict(id=rid, question=qid, family=meta['family'], subtype=meta['subtype'],
                       mechanism=mechanism, question_type=spec['type'], template=meta['template'],
                       state=record['state'], instructions=spec['instructions'], criteria=spec.get('criteria'),
                       gold=spec['label'], facts=f, tags={})
            if meta['family']=='ambiguous':
                row['tags'] = dict(twin=meta['twin'], absent_kind=meta['absent_kind'],
                                   explicit_unknown=meta['explicit_unknown'],
                                   answer_status='unknown' if spec['label']==f['insufficient_key'] else 'determinate')
            if meta['family']=='long_policy':
                truth = solve(f)
                exc = any(e['has_exception'] and f['case']['category'] in e['categories']
                          and condition(e,f['case']) and f['case']['exceptions'].get(e['key'],False)
                          for e in f['exclusions'])
                row['tags'] = dict(target=meta['target'], fee_order=f['fee_order'],
                    payable=truth['amount']>0, amount=truth['amount'], active_exception=exc,
                    item_class=f['case']['item_class'], domain=f['domain'])
            for name, snapshot in snapshots.items():
                r = snapshot[(rid,qid)]
                idx = max(range(len(r['p'])), key=r['p'].__getitem__)
                gold = str(spec['label']).lower()
                assert str(r['keys'][r['label']]).lower() == gold, (name,rid,qid,'gold')
                row[name+'_ok'] = correct(r)
                row[name+'_prediction'] = r['keys'][idx]
            result.append(row)
    groups = defaultdict(list)
    for r in result:
        groups['family/'+r['family']].append(r)
        groups[r['family']+'/mechanism/'+r['mechanism']].append(r)
        groups[r['family']+'/question/'+r['question']].append(r)
        if r['family']=='ambiguous':
            for key in ('twin','answer_status'):
                groups['ambiguous/'+key+'/'+str(r['tags'][key])].append(r)
            if r['tags']['twin']=='absent':
                groups['ambiguous/absent_kind/'+r['tags']['absent_kind']].append(r)
                groups['ambiguous/explicit_unknown/'+str(r['tags']['explicit_unknown'])].append(r)
        if r['family']=='long_policy':
            for key in ('target','fee_order','payable','active_exception'):
                groups['long_policy/'+key+'/'+str(r['tags'][key])+'/'+r['question']].append(r)
    summary = {g:{m:stats(rs,m) for m in ('q3','q35')} for g,rs in sorted(groups.items())}
    synth_path = ROOT/'artifacts/kev_training_eval_20261026/targeted_v2_all7_compact/train.jsonl'
    synth = read_jsonl(synth_path)
    synth_groups = {k:[r for r in synth if r['_meta']['family']==k]
                    for k in ('probability','insufficient','policy')}
    coverage = {}
    for fam, rs in synth_groups.items():
        coverage[fam] = dict(records=len(rs),subtypes=dict(Counter(r['_meta']['subtype'] for r in rs)),
            question_types=dict(Counter(q['type'] for r in rs for q in r['questions'].values())))
    ir = synth_groups['insufficient']
    coverage['insufficient']['semantic_labels'] = dict(Counter(r['_meta']['canonical_gold'] for r in ir))
    coverage['insufficient']['missing_value'] = sum(r['_meta']['facts']['value'] is None for r in ir)
    pr = synth_groups['policy']
    coverage['policy']['outcomes'] = dict(Counter(r['_meta']['option_values']['outcome'][r['questions']['outcome']['label']] for r in pr))
    coverage['policy']['zero_amount'] = sum(r['_meta']['option_values']['amount'][r['questions']['amount']['label']]=='0' for r in pr)
    coverage['policy']['explicit_event_contradictions'] = sum(not r['_meta']['facts']['covered_event'] for r in pr)
    multi = 0
    for r in pr:
        f = r['_meta']['facts']
        reasons = [not f['purchased'], not f['covered_event'], f['excluded'], f['report_days']>f['notice_days']]
        multi += sum(reasons)>1
    coverage['policy']['multiple_denial_reasons'] = multi
    ev = [r for r in synth_groups['probability'] if r['_meta']['facts']['kind']=='expected_value']
    ev_flips = []
    for r in ev:
        projects = r['_meta']['facts']['projects']
        pos = {name:Fraction(p['p'])*p['gain']+(1-Fraction(p['p']))*abs(p['loss'])-p['cost'] for name,p in projects.items()}
        answer = r['_meta']['option_values']['decision'][r['questions']['decision']['label']]
        if pos[answer]<max(pos.values()): ev_flips.append(r['_meta']['id'])
    coverage['probability']['expected_value_unsigned_loss_records'] = len(ev)
    coverage['probability']['unsigned_loss_changes_best_project'] = len(ev_flips)
    coverage['probability']['unsigned_loss_changed_ids'] = ev_flips
    manifest = dict(test_sha256=hashlib.sha256(test_path.read_bytes()).hexdigest(),
        synthetic_sha256=hashlib.sha256(synth_path.read_bytes()).hexdigest(),
        prediction_sha256={n:hashlib.sha256((OUT/'raw'/f'{n}.json').read_bytes()).hexdigest() for n in snapshots},
        records=len(records),questions=len(result),solver_labels_verified=len(result),
        scope='Full selected frozen hard-v1 test families; diagnostic reused test, not new held-out validation',
        cause_limit='Metadata classifies required mechanisms, not causal model error attribution.')
    (OUT/'summary.json').write_text(json.dumps(dict(provenance=manifest,groups=summary,synthetic=coverage),ensure_ascii=False,indent=2)+'\n')
    (OUT/'all_questions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in result))
    errors = [r for r in result if any(not r[m+'_ok'] for m in snapshots)]
    (OUT/'all_errors.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in errors))
    with (OUT/'group_metrics.csv').open('w') as h:
        w=csv.DictWriter(h,fieldnames=['group','model','n','before','after','repaired','broken','persistent_wrong'])
        w.writeheader()
        for g, models in summary.items():
            for m,s in models.items(): w.writerow(dict(group=g,model=m,**s))
    print(json.dumps(dict(provenance=manifest,error_union_questions=len(errors),groups=summary,synthetic=coverage),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
