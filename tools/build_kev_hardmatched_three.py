#!/usr/bin/env python3
"""Build an exact-schema three-family candidate from official hard-v1 development.

The 240 training skeletons and 60 validation skeletons are disjoint. Three
training views share facts and labels and must not be counted as independent
cases. hard-v1 test is used only for overlap and coverage auditing.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "third_party/kev-source-20261025/evals/hard-v1/development.jsonl"
TEST = ROOT / "third_party/kev-source-20261025/evals/hard-v1/test.jsonl"
OUT = ROOT / "artifacts/kev_training_eval_20261026/targeted_three_hardmatched_20261031"
VERSION = "targeted-three-hardmatched-20261031"
SOURCES = {
    "hard_temporal_numeric": "temporal",
    "hard_probability": "probability",
    "hard_multi_hop": "multihop",
}


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def canonical_state(state):
    if isinstance(state, str):
        return re.sub(r"\s+", " ", state).strip()
    return json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def choose_validation(rows, n=20):
    """Deterministic subtype-stratified allocation totaling n contexts."""
    by = defaultdict(list)
    for row in rows:
        by[row["_meta"]["subtype"]].append(row)
    for subtype in by:
        by[subtype].sort(key=lambda r: r["_meta"]["id"])
        random.Random(VERSION + "/split/" + subtype).shuffle(by[subtype])
    # Every observed subtype must appear in validation; distribute remaining
    # slots proportionally without exhausting any subtype's training examples.
    alloc = {k: 1 for k in by}
    remaining = n - sum(alloc.values())
    while remaining:
        candidates = [k for k in by if alloc[k] < len(by[k]) - 1]
        assert candidates
        k = max(candidates, key=lambda x: (len(by[x]) / (alloc[x] + 1), x))
        alloc[k] += 1
        remaining -= 1
    validation, train = [], []
    for subtype, group in sorted(by.items()):
        validation.extend(group[: alloc[subtype]])
        train.extend(group[alloc[subtype] :])
    assert len(validation) == n and len(train) == len(rows) - n
    return train, validation


def reorder_state(state, seed, style):
    if not isinstance(state, str) or style == 0:
        return state
    lines = state.splitlines()
    if len(lines) < 3:
        return state
    if lines[0] == "MEMO" and lines[1].startswith("Re: "):
        title = lines[1][4:]
        body = " ".join(line.strip() for line in lines[2:] if line.strip())
        cleaned = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)
    elif lines[0].startswith("CASE FILE:"):
        title = lines[0][len("CASE FILE:") :].strip()
        cleaned = [re.sub(r"^\d+\)\s*", "", line) for line in lines[1:]]
    else:
        return state
    # Preserve discourse order because some cases contain references such as
    # "these two". Views change presentation only, never fact order.
    if style == 1:
        body = [f"{i + 1}) {line}" for i, line in enumerate(cleaned)]
        header = f"CASE FILE: {title}"
    else:
        body = [f"- {line}" for line in cleaned]
        header = f"CASE NOTES: {title}"
    return "\n".join([header] + body)


def make_view(row, family, split, view):
    out = copy.deepcopy(row)
    original_id = row["_meta"]["id"]
    new_id = f"{VERSION}/{family}/{split}/{original_id.rsplit('/', 1)[-1]}/view-{view}"
    out["state"] = reorder_state(row["state"], new_id, view)
    meta = out["_meta"]
    meta.update(
        id=new_id,
        group_id=new_id,
        source=VERSION + "/" + family,
        split=split,
        template=meta["template"] + f"/view-{view}",
        family=family,
        seed_record_id=original_id,
        semantic_case_id=original_id,
        view=view,
        text_sha256=digest(out["state"]),
    )
    for q in out["questions"].values():
        q["src"] = VERSION + "/" + family
    return out


def signature(row):
    return {
        qid: {
            "type": q["type"],
            "instructions": q["instructions"],
            "criteria": q.get("criteria"),
            "label": q["label"],
        }
        for qid, q in row["questions"].items()
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    development = read(SOURCE)
    test = read(TEST)
    test_states = {canonical_state(r["state"]) for r in test}
    train_rows, validation_rows = [], []
    independent = {"train": Counter(), "development": Counter()}
    subtype_counts = {"train": Counter(), "development": Counter()}
    source_hashes = {}

    for source, family in SOURCES.items():
        rows = [r for r in development if r["_meta"]["source"] == source]
        assert len(rows) == 100
        train_base, validation_base = choose_validation(rows)
        independent["train"][family] = len(train_base)
        independent["development"][family] = len(validation_base)
        for base in train_base:
            for view in range(3):
                row = make_view(base, family, "train", view)
                assert signature(row) == signature(base)
                assert row["_meta"]["facts"] == base["_meta"]["facts"]
                assert canonical_state(row["state"]) not in test_states
                train_rows.append(row)
                subtype_counts["train"][family + "/" + base["_meta"]["subtype"]] += 1
        for base in validation_base:
            row = make_view(base, family, "development", 0)
            assert signature(row) == signature(base)
            assert row["_meta"]["facts"] == base["_meta"]["facts"]
            assert canonical_state(row["state"]) not in test_states
            validation_rows.append(row)
            subtype_counts["development"][family + "/" + base["_meta"]["subtype"]] += 1

    random.Random(VERSION + "/train").shuffle(train_rows)
    random.Random(VERSION + "/development").shuffle(validation_rows)
    train_path = OUT / "train.jsonl"
    dev_path = OUT / "development.jsonl"
    train_path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in train_rows))
    dev_path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in validation_rows))

    train_semantic = Counter(r["_meta"]["semantic_case_id"] for r in train_rows)
    dev_semantic = Counter(r["_meta"]["semantic_case_id"] for r in validation_rows)
    assert set(train_semantic).isdisjoint(dev_semantic)
    assert all(v == 3 for v in train_semantic.values())
    assert all(v == 1 for v in dev_semantic.values())
    assert len({r["_meta"]["id"] for r in train_rows}) == len(train_rows)
    assert len({r["_meta"]["id"] for r in validation_rows}) == len(validation_rows)

    for path in [SOURCE, TEST, train_path, dev_path]:
        source_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    test_subtypes = Counter(
        SOURCES[r["_meta"]["source"]] + "/" + r["_meta"]["subtype"]
        for r in test
        if r["_meta"]["source"] in SOURCES
    )
    manifest = {
        "version": VERSION,
        "status": "candidate_generated_not_trained",
        "method": "Official hard-v1 development cases, subtype-stratified 80/20 per family; three order-only training views per independent case.",
        "train_records": len(train_rows),
        "train_independent_cases": sum(independent["train"].values()),
        "train_questions": sum(len(r["questions"]) for r in train_rows),
        "development_records": len(validation_rows),
        "development_independent_cases": sum(independent["development"].values()),
        "development_questions": sum(len(r["questions"]) for r in validation_rows),
        "independent_cases": {k: dict(v) for k, v in independent.items()},
        "subtype_records": {k: dict(sorted(v.items())) for k, v in subtype_counts.items()},
        "hard_test_subtype_contexts": dict(sorted(test_subtypes.items())),
        "checks": {
            "train_development_semantic_case_overlap": 0,
            "canonical_state_overlap_with_hard_test": 0,
            "question_type_instructions_criteria_label_preserved_from_official_development": True,
            "facts_preserved_from_official_development": True,
            "train_views_per_independent_case": 3,
            "development_views_per_independent_case": 1,
            "all_three_target_families_exactly_80_train_20_development_cases": True,
        },
        "limitations": [
            "Only 240 independent training cases; 720 records include three surface-order views and are not 720 independent cases.",
            "Uses official hard-v1 development cases, so this is benchmark adaptation rather than external synthetic generalization.",
            "Test subtypes informed the family choice and audit; future hard-v1 test results are diagnostic, not blind evidence.",
            "No new facts were synthesized in this version; the intervention isolates exact-schema matching from fact-generation quality.",
        ],
        "sha256": source_hashes,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    examples = {}
    for family in SOURCES.values():
        examples[family] = [r for r in train_rows if r["_meta"]["family"] == family][:3]
    (OUT / "examples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
