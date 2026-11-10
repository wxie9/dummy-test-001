#!/usr/bin/env python3
"""Compare real hard-v1 probability/policy tests with targeted-v1 training data."""

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


FAMILIES = {
    "probability": ("hard_probability",),
    "long_policy": ("hard_long_policy",),
}


def char_len(state):
    return len(state) if isinstance(state, str) else len(json.dumps(state, sort_keys=True))


def summary(values):
    values = sorted(values)
    return {
        "min": values[0],
        "median": statistics.median(values),
        "mean": round(statistics.mean(values), 1),
        "max": values[-1],
    }


def load_jsonl(path):
    with open(path) as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rows_by_key(path):
    return {(r["id"], r["question"]): r for r in json.loads(Path(path).read_text())}


def correct(row):
    return max(range(len(row["p"])), key=row["p"].__getitem__) == row["label"]


if len(sys.argv) != 5:
    raise SystemExit("usage: analyze_probability_policy_shift.py HARD_TEST TARGET_TRAIN BEFORE_BENCH AFTER_BENCH")

hard_test, target_train, before_bench, after_bench = sys.argv[1:]
records = load_jsonl(hard_test)
target = load_jsonl(target_train)
before = rows_by_key(before_bench)
after = rows_by_key(after_bench)
result = {}

for family, (source,) in FAMILIES.items():
    real = [r for r in records if r["_meta"]["source"] == source]
    real_questions = []
    for record in real:
        for name in record["questions"]:
            real_questions.append((record["_meta"]["id"], name))
    selected = [key for key in real_questions if key in before and key in after]
    b = [correct(before[key]) for key in selected]
    a = [correct(after[key]) for key in selected]
    per_question = {}
    for name in sorted({name for _, name in selected}):
        keys = [key for key in selected if key[1] == name]
        bb = [correct(before[key]) for key in keys]
        aa = [correct(after[key]) for key in keys]
        per_question[name] = {
            "n": len(keys), "before_acc": round(100 * sum(bb) / len(bb), 2),
            "after_acc": round(100 * sum(aa) / len(aa), 2),
            "repaired": sum(not x and y for x, y in zip(bb, aa)),
            "newly_broken": sum(x and not y for x, y in zip(bb, aa)),
        }
    target_family = "policy" if family == "long_policy" else family
    synthetic = [r for r in target if r["_meta"]["family"] == target_family]
    result[family] = {
        "real_test": {
            "records": len(real), "questions": len(selected),
            "state_chars": summary([char_len(r["state"]) for r in real]),
            "question_breakdown": per_question,
        },
        "targeted_train": {
            "records": len(synthetic),
            "state_chars": summary([char_len(r["state"]) for r in synthetic]),
            "generator_kinds": dict(sorted(Counter(r["_meta"]["subtype"] for r in synthetic).items())),
        },
    }
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
