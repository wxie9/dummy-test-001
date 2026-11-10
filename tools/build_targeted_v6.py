#!/usr/bin/env python3
"""Assemble 1500 contexts, retaining the original three families exactly.

Additional views are subquestions, never additional independent scenarios.
No benchmark examples or answers are used to construct records.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_targeted_v5 import digest, check_graph_decision
from build_kev_probability_coverage_candidate import verify as check_probability
from build_kev_insufficient_multiview_candidates import verify as check_missing
from build_kev_multihop_coverage_candidates import verify as check_multihop
from check_targeted_v4_rules import policy, materialize, gold
from audit_kev_none_augmentation import is_none

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/kev_training_eval_20261026'
V5 = BASE / 'targeted_v5_20261030'
OUT = BASE / 'targeted_v6_20261030'
VERSION = 'targeted-v6-20261030'
RETAINED = {'tool_routing', 'temporal', 'injection'}


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def outcome_choices(state):
    """All eight descriptions are constructed from visible case facts only."""
    claim = state.split('INCIDENT FILE\n')[1]
    event = re.search(r'Event: ([^.]+)\.', claim)[1]
    item = re.search(r'Claimed item: ([^.]+)\.', claim)[1]
    code = re.search(r'BENEFIT (B\d): ' + re.escape(event) + r'\n', state)[1]
    prefix = f'Pay the covered {item} loss under {code} ({event}), '
    return {
        'loss based': prefix + 'using the eligible loss and deductible; neither a benefit ceiling nor a part ceiling reduces the amount entering the cap operation.',
        'benefit ceiling': prefix + 'with the benefit limit reducing the amount entering the cap operation; apply the deductible in the specified order.',
        'part ceiling': prefix + 'with the applicable part sublimit reducing the amount entering the cap operation; apply the deductible in the specified order.',
        'not purchased': f'Deny the {item} claim because the schedule does not purchase {code} ({event}).',
        'waiting period': f'Deny the {item} claim because the incident falls within the waiting period for {code} ({event}).',
        'usage maximum': f'Deny the {item} claim because its incident-time usage exceeds the maximum for {code} ({event}).',
        'unsafe storage': f'Deny the {item} claim because unsafe storage is recorded without a valid pre-incident waiver.',
        'late report': f'Deny the {item} claim because reporting falls outside the notice window.',
    }


def check_policy_outcomes(row):
    # Recover semantic labels from the visible option descriptions, not stored
    # facts or a saved expected answer, then recompute from visible policy text.
    r = copy.deepcopy(row)
    inverse = {v: k for k, v in outcome_choices(r['state']).items()}
    q = r['questions']['reason']
    assert len(set(q['criteria'].values())) == len(q['criteria']) == 8
    q['criteria'] = {k: inverse[v] for k, v in q['criteria'].items()}
    policy(r)


def validate(r):
    family = r['_meta']['family']
    materialize(r)
    if family == 'probability': check_probability(r)
    elif family == 'insufficient': check_missing(r)
    elif family == 'policy': check_policy_outcomes(r)
    elif family == 'multihop':
        if r['_meta']['subtype'] in {'dependency_candidates', 'rank_escalation'}: check_graph_decision(r)
        else: check_multihop(r)
    for q in r['questions'].values():
        if 'target' in q: assert q['target'] == {q['label']: 1.0}


def main():
    OUT.mkdir(exist_ok=True)
    manifest = {
        'version': VERSION, 'status': 'assembled_local_checks_passed_remote_preflight_pending',
        'goal_achieved': False, 'replay_contexts_separate': 6000,
        'init': 'original pre-targeted stage3, never a targeted stage4 checkpoint',
        'scope': '1500 distinct visible contexts, including correlated matched pairs and revised existing cases. Subquestions and views are not independent examples. Development shares generators; official tests were used for earlier diagnostics, not fresh holdout evidence.',
        'files': {}, 'sources': {},
        'limitations': ['Retained three families remain unchanged, including previously recorded temporal and tool-routing ambiguities.',
                       'Policy revisions change outcome wording and pair option contents, not the underlying case diversity.',
                       'Multiview questions change supervision density; this is not an equal-question-count ablation.',
                       'Same-author separate visible-text checks are not an external semantic review.'],
    }
    all_splits = {}; original_lines = {}; guards = []
    for split in ['train', 'development']:
        old_path = V5 / (split + '.jsonl')
        old = read(old_path)
        original_lines[split] = {json.loads(l)['_meta']['id']: l for l in old_path.read_text().splitlines()}
        rows = [r for r in old if r['_meta']['family'] in RETAINED]
        for component in ['probability_coverage', 'insufficient_multiview', 'policy_fixed_options', 'multihop_coverage']:
            source = BASE / (component + '_candidates_20261030') / (split + '.candidate.jsonl')
            manifest['sources'][str(source.relative_to(BASE))] = hashlib.sha256(source.read_bytes()).hexdigest()
            rows.extend(read(source))
        # Select by fixed seed, without predictions. Keep broad dependency and
        # rank routing coverage alongside the 180 newly authored graph cases.
        count = 45 if split == 'train' else 10
        for kind in ['dependency_candidates', 'rank_escalation']:
            pool = sorted((r for r in old if r['_meta']['family'] == 'multihop' and r['_meta']['subtype'] == kind), key=lambda r:r['_meta']['id'])
            rows.extend(random.Random(VERSION + '/' + split + '/' + kind).sample(pool, count))
        for r in rows:
            m = r['_meta']; family = m['family']
            if family in RETAINED: continue
            if family == 'policy':
                policy(r)
                choices = outcome_choices(r['state'])
                q = r['questions']['reason']
                q['criteria'] = {k: choices[v] for k, v in q['criteria'].items()}
                q['instructions'] = 'How should this claim be settled? Apply the stated denial priority first; otherwise select the payment basis under the settlement rule.'
            parent = m['id']; m['v6_parent_id'] = parent
            m['id'] = VERSION + '/' + parent
            m['group_id'] = VERSION + '/' + m['group_id']
            m['source'] = VERSION + '/' + family
            for name, q in r['questions'].items():
                q['src'] = m['source']
                if split == 'train' and q['type'] == 'choice' and any(is_none(k,v) for k,v in q['criteria'].items()):
                    assert family == 'multihop'
                    q['target'] = {q['label']: 1.0}
                    guards.append({'id':m['id'], 'question':name})
            validate(r)
        assert len(rows) == (1500 if split == 'train' else 336)
        random.Random(VERSION + '/' + split).shuffle(rows)
        all_splits[split] = rows
        # Retain exact original JSON lines for the three untouched components.
        lines = [original_lines[split][r['_meta']['id']] if r['_meta']['family'] in RETAINED else json.dumps(r,ensure_ascii=False,sort_keys=True) for r in rows]
        p = OUT / (split + '.jsonl'); p.write_text('\n'.join(lines)+'\n')
        assert all(r == json.loads(original_lines[split][r['_meta']['id']]) for r in rows if r['_meta']['family'] in RETAINED)
        families = Counter(r['_meta']['family'] for r in rows)
        per_questions = Counter()
        for r in rows: per_questions[r['_meta']['family']] += len(r['questions'])
        groups = defaultdict(list)
        for r in rows: groups[r['_meta']['group_id']].append(r)
        for members in groups.values():
            if members[0]['_meta']['family'] == 'policy':
                assert len(members) == 2
                for name in ['amount','reason']:
                    assert list(members[0]['questions'][name]['criteria'].items()) == list(members[1]['questions'][name]['criteria'].items())
        # Exercise every rewritten label once using a deliberately wrong label.
        # Strip target here so the test measures the visible-text checker.
        rejected = 0
        for r in rows:
            if r['_meta']['family'] in RETAINED: continue
            for name,q in r['questions'].items():
                bad = copy.deepcopy(r); bq = bad['questions'][name]; bq.pop('target',None)
                if q['type'] == 'choice': bq['label'] = next(k for k in q['criteria'] if k != q['label'])
                elif q['type'] == 'noul': bq['label'] = not q['label']
                elif q['type'] == 'score': bq['label'] = (q['label']+1)%len(q['criteria'])
                else: raise AssertionError(q['type'])
                try: validate(bad)
                except AssertionError: rejected += 1
                else: raise AssertionError(('wrong label accepted',r['_meta']['id'],name))
        manifest['files'][split] = {'contexts':len(rows), 'subquestions':sum(per_questions.values()),
            'families':dict(families), 'subquestions_by_family':dict(per_questions), 'groups':len(groups),
            'wrong_label_mutations_rejected_new_four':rejected, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    states = {s:{digest(r['state']) for r in rows} for s,rows in all_splits.items()}
    assert all(len(states[s]) == len(rows) for s,rows in all_splits.items())
    assert not states['train'] & states['development']
    assert not {r['_meta']['group_id'] for r in all_splits['train']} & {r['_meta']['group_id'] for r in all_splits['development']}
    frozen = {digest(r['state']) for p in (ROOT/'third_party/kev-source-20261025/evals').glob('*/test.jsonl') for r in read(p)}
    assert frozen
    assert not (states['train'] | states['development']) & frozen
    manifest['checks'] = {'duplicate_normalized_states':0,'exact_train_development_overlap':0,
        'group_overlap':0,'exact_frozen_test_state_overlap':0,'frozen_test_distinct_states':len(frozen),
        'retained_three_exact_original_lines':True,'policy_pair_serialized_options_identical':True,
        'semantic_overlap_not_ruled_out':True}
    manifest['explicit_none_protected_questions'] = len(guards)
    (OUT/'none_guard_records.json').write_text(json.dumps(guards,ensure_ascii=False,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
