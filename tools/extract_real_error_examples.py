#!/usr/bin/env python3
"""Extract representative paired frozen-test examples for four weak families."""

import json
from pathlib import Path


ROOT = Path('/C20545/kev-08b-official-repro-20261026')


def predicted(row):
    return max(range(len(row['p'])), key=row['p'].__getitem__)


def rows(path):
    return {(item['id'], item['question']): item for item in json.loads(path.read_text())}


def record_map(path):
    result = {}
    for line in path.read_text().splitlines():
        item = json.loads(line)
        result[item['_meta']['id']] = item
    return result


def format_example(records, before, after, source, question, wanted):
    for key, old in before.items():
        item_id, question_name = key
        if item_id not in records or (question is not None and question_name != question):
            continue
        record = records[item_id]
        if record['_meta']['source'] != source:
            continue
        new = after[key]
        old_ok, new_ok = predicted(old) == old['label'], predicted(new) == new['label']
        if (old_ok, new_ok) != wanted:
            continue
        spec = record['questions'][question_name]
        keys = old['keys']
        return {
            'id': item_id,
            'source': source,
            'state': record['state'],
            'question_name': question_name,
            'question': spec['instructions'],
            'options': dict(zip(keys, spec['criteria'])) if isinstance(spec['criteria'], list) else {key_name: spec['criteria'][key_name] for key_name in keys},
            'gold': keys[old['label']],
            'before_prediction': keys[predicted(old)],
            'after_prediction': keys[predicted(new)],
            'transition': '{} -> {}'.format('correct' if old_ok else 'wrong', 'correct' if new_ok else 'wrong'),
        }
    raise RuntimeError('no matching example')


hard_records = record_map(ROOT / 'evals/hard-v1/test.jsonl')
q3_before = rows(ROOT / 'runs/qwen3-06b-20261026/benchmarks/hard-v1-test/rows.json')
q3_after = rows(ROOT / 'runs/qwen3-06b-20261029-targeted-v2-all7-compact/stage4/benchmarks/hard-v1-test/rows.json')
q35_before = rows(ROOT / 'runs/replica-20261026/benchmarks/hard-v1-test/rows.json')
q35_after = rows(ROOT / 'runs/replica-20261029-targeted-v2-all7-compact/stage4/benchmarks/hard-v1-test/rows.json')

examples = {
    'probability_qwen3_new_break': format_example(hard_records, q3_before, q3_after, 'hard_probability', 'bucket', (True, False)),
    'insufficient_qwen3_new_break': format_example(hard_records, q3_before, q3_after, 'hard_ambiguous', None, (True, False)),
    'multihop_qwen3_repaired': format_example(hard_records, q3_before, q3_after, 'hard_multi_hop', None, (False, True)),
    'long_policy_qwen35_amount_new_break': format_example(hard_records, q35_before, q35_after, 'hard_long_policy', 'amount', (True, False)),
}
print(json.dumps(examples, ensure_ascii=False, indent=2))
