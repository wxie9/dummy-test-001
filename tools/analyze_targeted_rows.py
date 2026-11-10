#!/usr/bin/env python3
"""Summarize KEV benchmark rows by targeted_v1 family."""

import json
import sys
from collections import defaultdict
from pathlib import Path


def accuracy(rows):
    grouped = defaultdict(lambda: [0, 0])
    for row in rows:
        # IDs are targeted-v1-20261028/<family>/<split>/<index>.
        family = row["id"].split("/")[1]
        predicted = max(range(len(row["p"])), key=row["p"].__getitem__)
        grouped[family][0] += predicted == row["label"]
        grouped[family][1] += 1
    return {
        family: {"correct": correct, "n": n, "acc": round(100 * correct / n, 2)}
        for family, (correct, n) in sorted(grouped.items())
    }


if len(sys.argv) != 3:
    raise SystemExit("usage: analyze_targeted_rows.py BEFORE_ROWS AFTER_ROWS")

before = accuracy(json.loads(Path(sys.argv[1]).read_text()))
after = accuracy(json.loads(Path(sys.argv[2]).read_text()))
families = sorted(set(before) | set(after))
result = {
    family: {
        "before": before[family]["acc"],
        "after": after[family]["acc"],
        "delta_pp": round(after[family]["acc"] - before[family]["acc"], 2),
        "n": after[family]["n"],
    }
    for family in families
}
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
