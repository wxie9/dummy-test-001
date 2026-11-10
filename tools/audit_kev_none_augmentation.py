#!/usr/bin/env python3
"""Replay actual epoch augmentation without loading a model or changing training."""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

EXPLICIT_TEXT = {
    'none of the listed candidates', 'none of the above', 'none of these',
    'not listed here', 'none of the listed options apply',
    'an answer not covered by the other options', 'no option matches',
    'a reason that fits none of the above', 'a category that fits none of the above',
}
EXPLICIT_KEYS = {'none', 'none_of_the_above', 'none_of_these', 'not_listed', 'no_match'}


def is_none(key, text):
    return (text is None and key in EXPLICIT_KEYS) or (isinstance(text, str) and text.strip().casefold() in EXPLICIT_TEXT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--code-root', type=Path, required=True)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--replay-suite', type=Path)
    ap.add_argument('--replay-count', type=int, default=6000)
    args = ap.parse_args()
    sys.path.insert(0, str(args.code_root))
    from kev.data import augment, none_pair, source_seed
    rows = [json.loads(l) for l in args.data.read_text().splitlines()]
    targeted_count = len(rows)
    replay_ids = []
    if args.replay_suite:
        from kev.suite import load_split
        pool = load_split(args.replay_suite, 'train')
        replay = random.Random('replay:101').sample(pool, min(args.replay_count, len(pool)))
        replay_ids = [r['_meta']['id'] for r in replay]
        rows += [{**r, '_audit_replay': True} for r in replay]
    summary, examples = {}, []
    original_none = sum(any(is_none(k, v) for k, v in q.get('criteria', {}).items()) for r in rows for q in r['questions'].values() if q['type'] == 'choice')
    for epoch in range(3):
        counts = Counter()
        by_family = {}
        for req in rows:
            family = ('replay/' + req['_meta']['source']) if req.get('_audit_replay') else req['_meta']['family']
            f = by_family.setdefault(family, Counter())
            rng = random.Random(source_seed(101, f"{epoch}:{req['_meta']['id']}"))
            variants = [('ordinary', augment(req, rng, p_none=.1, p_none_distract=.12, p_distract=.15))]
            if rng.random() < .25:
                variants += list(zip(['pair_present', 'pair_absent'], none_pair(req, rng)))
            for variant_name, variant in variants:
                for qid, q in variant['questions'].items():
                    counts['questions'] += 1
                    f['questions'] += 1
                    if q['type'] != 'choice':
                        continue
                    counts['choice_questions'] += 1
                    f['choice_questions'] += 1
                    none_keys = [k for k, v in q['criteria'].items() if is_none(k, v)]
                    if len(none_keys) >= 2:
                        counts['multiple_explicit_none_options'] += 1
                        f['multiple_explicit_none_options'] += 1
                        if q['label'] in none_keys:
                            counts['gold_has_equivalent_correct_alternative'] += 1
                            f['gold_has_equivalent_correct_alternative'] += 1
                            if len(examples) < 8:
                                examples.append({'epoch': epoch, 'variant': variant_name, 'id': req['_meta']['id'],
                                    'family': family, 'question': qid, 'state': req['state'],
                                    'question_spec': q, 'equivalent_none_keys': none_keys})
        summary[str(epoch)] = {'total': counts, 'by_family': by_family}
    out = {
        'scope': 'Exact seeded replay of source records and, when requested, the same replay:101 sample. No model inference or token filtering; current training preflight verified all 7500 records fit. Ambiguous supervision is a data finding, not causal proof of score changes.',
        'data_sha256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
        'code_data_py_sha256': hashlib.sha256((args.code_root/'kev/data.py').read_bytes()).hexdigest(),
        'targeted_contexts': targeted_count, 'replay_contexts': len(replay_ids),
        'replay_ids_sha256': hashlib.sha256(json.dumps(replay_ids).encode()).hexdigest() if replay_ids else None,
        'original_questions_with_explicit_none': original_none,
        'seed': 101, 'settings': {'p_none': .1, 'p_none_distract': .12, 'p_distract': .15, 'p_none_pair': .25},
        'epochs': summary, 'examples': examples,
        'interpretation': 'When two semantically equivalent none options are present and one is gold, one-hot training penalizes selecting the other equally valid option. Implicit other/unknown wordings are excluded from this conservative count.',
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['examples','interpretation']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
