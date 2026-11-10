#!/usr/bin/env python3
"""Protect existing none choices using the trainer's one-hot target mechanism.

The target has exactly the same cross-entropy objective as the hard label when
loss modifiers are zero. Existing trainer code then permits permutation only
and excludes these questions from none-pair insertion. No source code changes.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from audit_kev_none_augmentation import is_none


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    assert args.input.resolve() != args.output.resolve()
    original = args.input.read_bytes()
    lines, changes, families = [], [], Counter()
    total_questions = 0
    for line in original.decode().splitlines():
        r = json.loads(line)
        family = r['_meta']['family']
        families[family] += 1
        total_questions += len(r['questions'])
        changed = False
        for name, q in r['questions'].items():
            if q['type'] == 'choice' and any(is_none(k, v) for k, v in q['criteria'].items()):
                assert family == 'multihop', 'Unexpected family requires review; retained three must remain unchanged.'
                assert q.get('target') is None
                q['target'] = {q['label']: 1.0}
                changes.append({'id': r['_meta']['id'], 'question': name, 'label': q['label']})
                changed = True
        lines.append(json.dumps(r, ensure_ascii=False, sort_keys=True) if changed else line)
    assert len(lines) == 1500 and len(changes) == 90
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines)+'\n')
    old = [json.loads(l) for l in original.decode().splitlines()]
    new = [json.loads(l) for l in args.output.read_text().splitlines()]
    for a,b in zip(old,new):
        for q in b['questions'].values():
            q.pop('target', None)
        assert a == b
    manifest = {
        'status': 'candidate_only_not_in_training',
        'source_sha256': hashlib.sha256(original).hexdigest(),
        'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'contexts': len(lines), 'questions': total_questions, 'families': families,
        'modified_questions': len(changes), 'changes': changes,
        'all_states_labels_options_and_ids_unchanged': True,
        'retained_three_original_lines_unchanged': True,
        'mechanism': 'Existing target field with all mass on hard gold; allows only option permutation and excludes none-pair construction.',
        'limitation': 'Changes augmentation and variant counts for 90 multihop questions; not an equal-number-of-variants ablation. Hard-label and target loss equivalence requires zero loss modifiers, as in current runs. No effect claim before evaluation.',
    }
    args.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k != 'changes'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
