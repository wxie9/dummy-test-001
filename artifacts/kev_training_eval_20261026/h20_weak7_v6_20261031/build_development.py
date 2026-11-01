#!/usr/bin/env python3
"""Build disjoint development panels for the two weak-seven training sets."""

import argparse
import collections
import hashlib
import json
import copy
from pathlib import Path


FAMILIES = {
    "4b": {"tool_routing", "temporal", "probability", "injection", "codereviewer", "commitpackft", "flakeflagger"},
    "9b": {"tool_routing", "temporal", "probability", "policy", "multihop", "codereviewer", "commitpackft"},
}


def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def state_hash(row):
    return hashlib.sha256(json.dumps(row["state"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v6", required=True)
    ap.add_argument("--devtools", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    v6 = read(a.v6)
    devtools = read(a.devtools)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for model, families in FAMILIES.items():
        rows = [copy.deepcopy(r) for r in v6 if r["_meta"].get("family") in families]
        rows += [copy.deepcopy(r) for r in devtools if r["_meta"].get("source") in families]
        for row in rows:
            row["_meta"]["variant"] = "clean"
        train = read(outdir / f"train_{model}.jsonl")
        train_states = {state_hash(r) for r in train}
        if any(state_hash(r) in train_states for r in rows):
            raise AssertionError(f"Development state overlaps training: {model}")
        output = outdir / f"development_{model}.jsonl"
        with output.open("w") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        report[model] = {
            "records": len(rows),
            "questions": sum(len(r["questions"]) for r in rows),
            "families": dict(collections.Counter(r["_meta"].get("family", r["_meta"].get("source")) for r in rows)),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        }
    (outdir / "development_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
