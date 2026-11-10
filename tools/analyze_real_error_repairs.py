#!/usr/bin/env python3
"""Pair original Kev test rows before/after a continuation run by diagnosed error family."""

import json
import sys
from pathlib import Path


FAMILIES = {
    "tool_clarification": ("devtools-v1-test", "when2call", "action"),
    "prompt_injection": ("devtools-v1-test", "prompt_injection", "injection"),
    "temporal_numeric": ("hard-v1-test", "hard_temporal_numeric", None),
    "probability": ("hard-v1-test", "hard_probability", None),
    "insufficient_evidence": ("hard-v1-test", "hard_ambiguous", None),
    "multi_hop": ("hard-v1-test", "hard_multi_hop", None),
    "long_policy": ("hard-v1-test", "hard_long_policy", None),
}


def load_rows(root, suite):
    path = Path(root) / "benchmarks" / suite / "rows.json"
    return {(r["id"], r["question"]): r for r in json.loads(path.read_text())}


def is_correct(row):
    return max(range(len(row["p"])), key=row["p"].__getitem__) == row["label"]


if len(sys.argv) != 3:
    raise SystemExit("usage: analyze_real_error_repairs.py BEFORE_RUN AFTER_RUN")

before_root, after_root = sys.argv[1:]
all_rows = {}
for suite in {value[0] for value in FAMILIES.values()}:
    all_rows[suite] = (load_rows(before_root, suite), load_rows(after_root, suite))

out = {}
for family, (suite, source, question) in FAMILIES.items():
    before, after = all_rows[suite]
    selected = [
        key for key, row in before.items()
        if row["source"] == source and (question is None or row["question"] == question)
    ]
    if set(selected) - set(after):
        raise RuntimeError(f"missing post-training rows for {family}")
    b = [is_correct(before[key]) for key in selected]
    a = [is_correct(after[key]) for key in selected]
    repaired = sum(not was and now for was, now in zip(b, a))
    broken = sum(was and not now for was, now in zip(b, a))
    out[family] = {
        "n": len(selected),
        "before_acc": round(100 * sum(b) / len(b), 2),
        "after_acc": round(100 * sum(a) / len(a), 2),
        "delta_pp": round(100 * (sum(a) - sum(b)) / len(b), 2),
        "before_wrong": len(b) - sum(b),
        "repaired": repaired,
        "repair_rate_of_original_errors": round(100 * repaired / (len(b) - sum(b)), 2) if len(b) != sum(b) else None,
        "newly_broken": broken,
    }
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
