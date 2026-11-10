#!/usr/bin/env python3
"""Build a fresh, solver-labelled all-seven-family Kev continuation set.

This is for a clean continuation branch from the pre-targeted Kev checkpoint.
It deliberately does *not* resume an adapter trained on targeted-v1.  The
five rule families use independent renders from the original deterministic
programs; probability and long-policy use the richer v2 programs.  Exact
rendered states are excluded against both earlier targeted suites and across
the three new partitions.
"""

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import build_targeted_v1 as legacy
import build_targeted_v2_probability_policy as rich


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "kev_training_eval_20261026" / "targeted_v2_all7_compact"
VERSION = "targeted-v2-all7-compact-20261029"
SEED = 20261029

# The seven categories diagnosed from the fixed Kev runs.  Probability and
# policy receive more examples because they were the two categories whose
# targeted-v1 continuation regressed on real held-out errors.
SIZES = {
    "train": {
        "tool_routing": 900, "temporal": 800, "probability": 1400,
        "insufficient": 700, "multihop": 800, "policy": 1200,
        "injection": 600,
    },
    "development": {
        "tool_routing": 100, "temporal": 100, "probability": 150,
        "insufficient": 100, "multihop": 100, "policy": 150,
        "injection": 100,
    },
    "test": {
        "tool_routing": 100, "temporal": 100, "probability": 150,
        "insufficient": 100, "multihop": 100, "policy": 150,
        "injection": 100,
    },
}

LEGACY_FAMILIES = ("tool_routing", "temporal", "insufficient", "multihop", "injection")
RICH_FAMILIES = ("probability", "policy")


def state_hash(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def previous_state_hashes():
    """Prevent accidental literal reuse of either earlier targeted suite."""
    hashes = set()
    for name in ("targeted_v1", "targeted_v2_probability_policy"):
        for path in (ROOT / "artifacts" / "kev_training_eval_20261026" / name).glob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                hashes.add(state_hash(json.loads(line)["state"]))
    return hashes


def legacy_record(split, family, ordinal, attempt):
    rng = random.Random("{}:{}:{}:{}".format(VERSION, split, family, attempt))
    record = legacy.GENERATORS[family](split, ordinal, rng)
    record["_meta"]["id"] = "{}/{}/{}/{:05d}".format(VERSION, family, split, ordinal)
    record["_meta"]["group_id"] = record["_meta"]["id"]
    record["_meta"]["source"] = "targeted_v2_all7_{}".format(family)
    record["_meta"]["text_sha256"] = state_hash(record["state"])
    return record


def rich_record(split, family, ordinal, attempt):
    rng = random.Random("{}:{}:{}:{}".format(SEED, split, family, attempt))
    maker = rich.gen_probability if family == "probability" else rich.gen_policy
    record = maker(split, ordinal, rng)
    record["_meta"]["id"] = "{}/{}/{}/{:05d}".format(VERSION, family, split, ordinal)
    record["_meta"]["group_id"] = record["_meta"]["id"]
    record["_meta"]["source"] = "targeted_v2_all7_{}".format(family)
    record["_meta"]["text_sha256"] = state_hash(record["state"])
    return record


def verify(record):
    family = record["_meta"]["family"]
    if family in LEGACY_FAMILIES:
        expected = legacy.recompute(record)
        question = record["questions"]["decision"]
        values = record["_meta"]["option_values"]
        if values.get(question["label"]) != expected:
            raise AssertionError("legacy label mismatch: {}".format(family))
        return
    rich.verify_record(record)


def build_partition(split, blocked):
    records = []
    for family, count in SIZES[split].items():
        made, attempt = 0, 0
        while made < count:
            attempt += 1
            if attempt > count * 100:
                raise RuntimeError("dedup exhausted: {}/{}".format(split, family))
            try:
                record = (legacy_record(split, family, made, attempt)
                          if family in LEGACY_FAMILIES
                          else rich_record(split, family, made, attempt))
            # Some legacy temporal distractor combinations collapse to the
            # same visible date.  Discard that candidate rather than training
            # on a non-unique multiple-choice question.
            except ValueError:
                continue
            digest = record["_meta"]["text_sha256"]
            if digest in blocked:
                continue
            verify(record)
            blocked.add(digest)
            records.append(record)
            made += 1
    random.Random("{}:{}:shuffle".format(VERSION, split)).shuffle(records)
    return records


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    # Imported builders embed their own version in record ids.  Set it before
    # generating, then explicitly rewrite ids as a second audit guard.
    legacy.VERSION = VERSION
    rich.VERSION = VERSION
    OUT.mkdir(parents=True, exist_ok=True)
    blocked = previous_state_hashes()
    parts = {}
    # Build evaluation partitions first, then development, then train.
    for split in ("test", "development", "train"):
        parts[split] = build_partition(split, blocked)
        write_jsonl(OUT / (split + ".jsonl"), parts[split])

    files = {}
    for split in ("train", "development", "test"):
        path = OUT / (split + ".jsonl")
        records = parts[split]
        files[path.name] = {
            "records": len(records),
            "questions": sum(len(record["questions"]) for record in records),
            "by_family": dict(sorted(Counter(record["_meta"]["family"] for record in records).items())),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest = {
        "version": VERSION,
        "purpose": "fresh all-seven-family continuation data; do not resume a targeted-v1 adapter",
        "families": list(SIZES["train"]),
        "label_protocol": "deterministic solvers; every label is recomputed before write",
        "isolation": "test, then development, then train; split-specific renders; global exact-state exclusion against targeted-v1, targeted-v2 probability/policy, and all new partitions",
        "probability_policy": "richer v2 mechanisms replace the earlier simplified generators",
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# targeted-v2 all seven families\n\n"
        "Fresh solver-labelled continuation data for tool routing, temporal reasoning, probability, insufficient evidence, multihop reasoning, long policy, and prompt-injection recognition. "
        "Use `train.jsonl` only for training; keep development/test locked.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
