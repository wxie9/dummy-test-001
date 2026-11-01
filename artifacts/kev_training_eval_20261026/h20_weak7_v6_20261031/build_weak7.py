#!/usr/bin/env python3
"""Assemble two 1,500-record weak-category continuation corpora.

The v6 records are already solver-labelled and frozen. Developer-tool records
are sampled only from the original train partition after removing any record
whose ID, state, or supplied text hash occurs in an evaluation partition.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
from pathlib import Path


TARGETS = {
    "4b": {
        "tool_routing": 100,
        "temporal": 100,
        "probability": 350,
        "injection": 100,
        "codereviewer": 300,
        "commitpackft": 300,
        "flakeflagger": 250,
    },
    "9b": {
        "tool_routing": 100,
        "temporal": 100,
        "probability": 350,
        "policy": 300,
        "multihop": 270,
        "codereviewer": 190,
        "commitpackft": 190,
    },
}
DEVTOOLS = {"codereviewer", "commitpackft", "flakeflagger"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_hash(row: dict) -> str:
    payload = json.dumps(row["state"], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def stratum(row: dict, source: str) -> str:
    question = {
        "codereviewer": "needs_comment",
        "commitpackft": "change_type",
        "flakeflagger": "flaky",
    }[source]
    return str(row["questions"][question]["label"])


def balanced_sample(rows: list[dict], n: int, source: str, model: str) -> list[dict]:
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        groups[stratum(row, source)].append(row)
    rng = random.Random(f"kev-weak7-v6:{model}:{source}:101")
    for group in groups.values():
        rng.shuffle(group)
    labels = sorted(groups)
    quotas = {label: n // len(labels) for label in labels}
    for label in labels[: n % len(labels)]:
        quotas[label] += 1
    if any(quotas[label] > len(groups[label]) for label in labels):
        raise ValueError(f"Insufficient records for balanced {source}: {quotas}")
    return [row for label in labels for row in groups[label][: quotas[label]]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v6", type=Path, required=True)
    ap.add_argument("--devtools", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    v6 = read_jsonl(args.v6)
    train_path = args.devtools / "train.jsonl"
    train = read_jsonl(train_path)
    held_paths = [args.devtools / f"{part}.jsonl" for part in ("calibration", "development", "test")]
    held_paths = [p for p in held_paths if p.exists()]
    held = [row for path in held_paths for row in read_jsonl(path)]
    held_ids = {row["_meta"].get("id") for row in held}
    held_states = {state_hash(row) for row in held}
    held_texts = {row["_meta"].get("text_sha256") for row in held}
    eligible: dict[str, list[dict]] = {}
    exclusion_counts: dict[str, dict] = {}
    for source in sorted(DEVTOOLS):
        pool = [row for row in train if row["_meta"].get("source") == source]
        id_counts = collections.Counter(row["_meta"].get("id") for row in pool)
        clean = [
            row for row in pool
            if id_counts[row["_meta"].get("id")] == 1
            and row["_meta"].get("id") not in held_ids
            and state_hash(row) not in held_states
            and row["_meta"].get("text_sha256") not in held_texts
        ]
        eligible[source] = clean
        exclusion_counts[source] = {"train": len(pool), "excluded": len(pool) - len(clean), "eligible": len(clean)}
    v6_by_family: dict[str, list[dict]] = collections.defaultdict(list)
    for row in v6:
        v6_by_family[row["_meta"]["family"]].append(row)

    manifest = {
        "seed": 101,
        "method": "frozen v6 solver-labelled rows plus held-out-screened original devtools train rows",
        "v6_sha256": sha256(args.v6),
        "devtools_train_sha256": sha256(train_path),
        "heldout_sha256": {p.name: sha256(p) for p in held_paths},
        "devtools_screen": exclusion_counts,
        "models": {},
    }
    for model, target in TARGETS.items():
        output: list[dict] = []
        for source, n in target.items():
            if source in DEVTOOLS:
                output += balanced_sample(eligible[source], n, source, model)
            else:
                rows = v6_by_family[source]
                if len(rows) != n:
                    raise ValueError(f"Expected {n} v6 {source} rows; found {len(rows)}")
                output += rows
        if len(output) != 1500:
            raise AssertionError((model, len(output)))
        random.Random(f"kev-weak7-v6:order:{model}:101").shuffle(output)
        out_path = args.out / f"train_{model}.jsonl"
        with out_path.open("w") as f:
            for row in output:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        ids = [row["_meta"]["id"] for row in output]
        if len(set(ids)) != len(ids):
            raise AssertionError(f"Duplicate IDs in {model}")
        if any(row["_meta"].get("id") in held_ids or state_hash(row) in held_states for row in output):
            raise AssertionError(f"Held-out overlap in {model}")
        manifest["models"][model] = {
            "target_families": target,
            "records": len(output),
            "questions": sum(len(row["questions"]) for row in output),
            "sha256": sha256(out_path),
            "source_counts": dict(collections.Counter(row["_meta"]["source"] for row in output)),
        }
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
