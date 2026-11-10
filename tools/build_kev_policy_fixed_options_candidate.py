#!/usr/bin/env python3
"""Freeze identical choices within each policy pair; never launch training.

This is a replacement component with the same states and semantic golds.
It does not create additional independent contexts or alter frozen v5 data.
"""
import copy
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from check_targeted_v4_rules import policy, materialize, gold

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / 'artifacts/kev_training_eval_20261026/targeted_v5_20261030'
OUT = V5.with_name('policy_fixed_options_candidates_20261030')
VERSION = 'policy-fixed-options-candidate-20261030'


def audit(groups):
    counts = defaultdict(Counter)
    for pair in groups.values():
        assert len(pair) == 2
        a, b = pair
        for name in a['questions']:
            x, y = a['questions'][name], b['questions'][name]
            c = counts[a['_meta']['pair_kind'] + '/' + name]
            c['pairs'] += 1
            c['same_option_contents'] += set(x['criteria'].values()) == set(y['criteria'].values())
            c['same_key_mapping_and_order'] += list(x['criteria'].items()) == list(y['criteria'].items())
            c['semantic_gold_changed'] += gold(a, name) != gold(b, name)
    return dict(counts)


def main():
    OUT.mkdir(exist_ok=True)
    manifest = {
        'status': 'candidate_only_not_in_training',
        'purpose': 'Replace the policy component without changing state, semantic gold, number of contexts, or questions.',
        'scope': 'Previously diagnosed development cases, not fresh held-out generalization evidence. Candidate count is not added to the 1500 contexts.',
        'files': {},
    }
    for split in ['train', 'development']:
        originals = [json.loads(l) for l in (V5 / (split + '.jsonl')).read_text().splitlines()]
        originals = [r for r in originals if r['_meta']['family'] == 'policy']
        grouped = defaultdict(list)
        for r in originals:
            grouped[r['_meta']['group_id']].append(r)
        before = audit(grouped)
        newgroups = {}
        for group, oldpair in grouped.items():
            pair = copy.deepcopy(oldpair)
            rng = random.Random(VERSION + '/' + group)
            for name in ['amount', 'reason']:
                correct = list(dict.fromkeys(gold(r, name) for r in oldpair))
                # Keep both correct answers and every existing distinct distractor.
                # No choice is selected using a model prediction or benchmark score.
                values = list(dict.fromkeys(v for r in oldpair for v in r['questions'][name]['criteria'].values()))
                assert all(v in values for v in correct)
                rng.shuffle(values)
                criteria = {chr(97+i): value for i, value in enumerate(values)}
                for old, r in zip(oldpair, pair):
                    q = r['questions'][name]
                    q['criteria'] = dict(criteria)
                    q['label'] = next(k for k, v in criteria.items() if v == gold(old, name))
                    q['src'] = VERSION
            for old, r in zip(oldpair, pair):
                m = r['_meta']
                m['derived_from'] = m['id']
                m['id'] = VERSION + '/' + m['id']
                m['group_id'] = VERSION + '/' + group
                m['source'] = VERSION
                assert r['state'] == old['state']
                for name in r['questions']:
                    assert gold(r, name) == gold(old, name)
                materialize(r)
                policy(r)
            newgroups[group] = pair
        after = audit(newgroups)
        for values in after.values():
            assert values['pairs'] == values['same_key_mapping_and_order'] == values['same_option_contents']
        rows = [r for pair in newgroups.values() for r in pair]
        mutations = 0
        for r in rows:
            for name in r['questions']:
                bad = copy.deepcopy(r)
                q = bad['questions'][name]
                q['label'] = next(k for k in q['criteria'] if k != q['label'])
                try:
                    policy(bad)
                except AssertionError:
                    mutations += 1
                else:
                    raise AssertionError('Incorrect label was accepted')
        path = OUT / (split + '.candidate.jsonl')
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        # Reload to check serialized option ordering, rather than only objects.
        reloaded = [json.loads(l) for l in path.read_text().splitlines()]
        for i in range(0, len(reloaded), 2):
            for name in reloaded[i]['questions']:
                assert list(reloaded[i]['questions'][name]['criteria'].items()) == list(reloaded[i+1]['questions'][name]['criteria'].items())
        manifest['files'][split] = {
            'contexts': len(rows), 'questions': 2 * len(rows),
            'wrong_label_mutations_rejected': mutations,
            'option_count_histogram': dict(Counter(len(r['questions']['amount']['criteria']) for r in rows)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'before': before, 'after': after,
        }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({s:{k:v for k,v in m.items() if k not in ['before','after']} for s,m in manifest['files'].items()}, indent=2))


if __name__ == '__main__':
    main()
