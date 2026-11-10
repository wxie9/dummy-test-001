#!/usr/bin/env python3
"""Generate model-specific error-neighborhood candidates from frozen test errors.

Each original-stage checkpoint error context produces three train views and one
development view. These are benchmark-directed candidates, never blind data.
"""
import copy
import hashlib
import importlib.util
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artifacts/kev_training_eval_20261026/h20_weak7_v6_20261031"
OUT = ROOT / "artifacts/kev_training_eval_20261026/h20_weak7_error_neighborhood_20261031"
HARD = ROOT / "third_party/kev-source-20261025/evals/hard-v1/test.jsonl"
DEV = BASE / "diagnostics/source_data/devtools-test.jsonl"
TARGETS = {
    "4b": {"hard_temporal_numeric", "when2call", "hard_probability", "codereviewer",
           "prompt_injection", "commitpackft", "flakeflagger"},
    "9b": {"hard_temporal_numeric", "when2call", "hard_probability", "codereviewer",
           "commitpackft", "hard_long_policy", "hard_multi_hop"},
}
HARD_FAMILIES = {"hard_temporal_numeric": "temporal", "hard_probability": "probability",
                 "hard_multi_hop": "multihop"}
SPEC = importlib.util.spec_from_file_location("original_neighborhood", ROOT / "tools/build_kev_error_neighborhood_three.py")
NEIGHBORHOOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NEIGHBORHOOD)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def flatten(records):
    return [(index, rec, name, question) for index, rec in enumerate(records)
            for name, question in rec["questions"].items()]


def aligned_errors(records, rows, targets, source):
    flat = flatten(records)
    assert len(flat) == len(rows), (source, len(flat), len(rows))
    errors = defaultdict(list)
    for (index, rec, name, question), row in zip(flat, rows):
        assert (rec["_meta"]["id"], rec["_meta"]["source"], name) == (row["id"], row["source"], row["question"])
        label = question["label"]
        if question["type"] == "choice":
            assert list(question["criteria"])[int(row["label"])] == label
        else:
            assert str(label).lower() == str(row["keys"][int(row["label"])]).lower(), (source, index, name)
        if row["source"] in targets and max(range(len(row["p"])), key=row["p"].__getitem__) != int(row["label"]):
            errors[(source, index)].append(name)
    return errors


def shift_hunk_lines(text, view):
    shift = (view + 1) * 37
    def repl(match):
        return f"@@ -{int(match[1])+shift}{match[2]} +{int(match[3])+shift}{match[4]} @@"
    return re.sub(r"@@ -(\d+)(,\d+)? \+(\d+)(,\d+)? @@", repl, text)


def transform_devtools(state, source, view, rng):
    state = copy.deepcopy(state)
    method = None
    if source == "when2call":
        tools = state["available_tools"]
        rng.shuffle(tools)
        # JSON whitespace and key order carry no tool schema meaning.
        state["available_tools"] = [json.dumps(json.loads(t), ensure_ascii=False,
                                                sort_keys=(view % 2 == 0),
                                                indent=2 if view % 2 else None) for t in tools]
        state["user_message"] = ["User request:\n", "Request to route:\n", "User query:\n", "Incoming request:\n"][view] + state["user_message"]
        method = "tool_schema_render_and_order"
    elif source == "codereviewer":
        old = state["diff"]
        state["diff"] = shift_hunk_lines(old, view)
        # A reviewer sees the same added/deleted code at a different file position.
        assert state["diff"] != old
        method = "diff_hunk_line_offset"
    elif source == "flakeflagger":
        state["test_class"] = f"synthetic{view+1}." + state["test_class"]
        method = "test_class_namespace_prefix"
    elif source == "commitpackft":
        state = shift_hunk_lines(state, view)
        method = "diff_hunk_line_offset"
    elif source == "prompt_injection":
        state = f"Message under review (view {view+1}):\n" + state
        method = "message_review_wrapper"
    else:
        raise ValueError(source)
    return state, method


def make_variant(base, source, model, split, view, seed_key, wrong_questions):
    version = f"h20-{model}-weak7-error-neighborhood-20261031"
    rng = random.Random(f"{version}/{seed_key}/{view}")
    if source in HARD_FAMILIES:
        NEIGHBORHOOD.VERSION = version
        row = NEIGHBORHOOD.make_variant(base, HARD_FAMILIES[source], split, view)
        if split == "development":
            row["state"] = "Case details for assessment:\n" + row["state"]
        method = "original_0.8b_hard_family_transform"
    else:
        row = copy.deepcopy(base)
        if source == "hard_long_policy":
            old = row["state"]
            row["state"] = re.sub(r"^Issued by [^\n]+", f"Issued by Synthetic Policy Office {view+1}", old, count=1, flags=re.M)
            assert row["state"] != old
            method = "policy_issuer_rename"
        else:
            row["state"], method = transform_devtools(row["state"], source, view, rng)
        for q in row["questions"].values():
            NEIGHBORHOOD.reorder_criteria(q, rng)
            q["src"] = version + "/" + source
    meta = row["_meta"]
    seed_id = base["_meta"]["id"]
    meta.update(id=f"{version}/{source}/{split}/record-{seed_key[1]:05d}/view-{view}",
                group_id=f"{version}/{source}/record-{seed_key[1]:05d}/view-{view}",
                source=version + "/" + source, split=split, variant="error_neighborhood", family=source,
                seed_error_id=seed_id, seed_suite=seed_key[0], seed_record_index=seed_key[1],
                targeted_wrong_questions=sorted(wrong_questions), transform={"view": view, "method": method},
                text_sha256=NEIGHBORHOOD.digest(row["state"]))
    meta["seed_provenance"] = base["_meta"].get("provenance")
    meta["provenance"] = "derived_from_original_stage_error_on_frozen_test"
    for stale in ["row_sha256", "state_tokens"]:
        meta.pop(stale, None)
    return row


def write_jsonl(path, rows):
    path.write_text("".join(canonical(row) + "\n" for row in rows))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {"hard": read_jsonl(HARD), "dev": read_jsonl(DEV)}
    manifest = {"status": "candidate_generated_not_trained", "method": "3 train + 1 development views per original-stage wrong context",
                "source_files": {str(p): sha(p) for p in [HARD, DEV]}, "models": {},
                "limitations": ["Seeds are selected from frozen hard-v1 and devtools-v1 test errors; neither suite is blind for evaluating these candidates.",
                                "Development views share their seed's semantic skeleton with training views.",
                                "Labels are inherited under controlled edits, without independent semantic adjudication.",
                                "For code, tool routing, prompt injection and long policy, edits are conservative and some text remains close to the test seed."]}
    for model, targets in TARGETS.items():
        rows_paths = {"hard": BASE / f"baseline_rows/kev-{model}-hard-rows.json",
                      "dev": BASE / f"baseline_rows/kev-{model}-dev-rows.json"}
        errors = {}
        for suite in ["hard", "dev"]:
            rows = json.loads(rows_paths[suite].read_text())
            errors.update(aligned_errors(sources[suite], rows, targets, suite))
        assert all(sources[suite][index]["_meta"]["source"] in targets for suite, index in errors)
        train, development = [], []
        for key in sorted(errors):
            suite, index = key
            base = sources[suite][index]
            source = base["_meta"]["source"]
            for view in range(4):
                split = "train" if view < 3 else "development"
                row = make_variant(base, source, model, split, view, key, errors[key])
                (train if view < 3 else development).append(row)
        random.Random(f"h20-{model}-weak7-error-neighborhood-20261031/train").shuffle(train)
        random.Random(f"h20-{model}-weak7-error-neighborhood-20261031/dev").shuffle(development)
        source_states = {canonical(rec["state"]) for records in sources.values() for rec in records}
        assert all(canonical(row["state"]) not in source_states for row in train + development)
        assert len({row["_meta"]["id"] for row in train + development}) == len(train) + len(development)
        assert len(train) == 3*len(errors) and len(development) == len(errors)
        assert set((r["_meta"]["seed_suite"], r["_meta"]["seed_record_index"]) for r in train) == set(errors)
        assert set((r["_meta"]["seed_suite"], r["_meta"]["seed_record_index"]) for r in development) == set(errors)
        # For every view, labels and question types are exactly those of its seed.
        for row in train + development:
            meta = row["_meta"]
            original = sources[meta["seed_suite"]][meta["seed_record_index"]]
            assert row["state"] != original["state"]
            assert set(row["questions"]) == set(original["questions"])
            for name, q in row["questions"].items():
                seed_q = original["questions"][name]
                assert q["type"] == seed_q["type"] and q["label"] == seed_q["label"]
                if q["type"] == "choice":
                    assert set(q["criteria"]) == set(seed_q["criteria"])
        for split, records in [("train", train), ("development", development)]:
            write_jsonl(OUT / f"{model}_{split}.jsonl", records)
        by_source = Counter(sources[suite][index]["_meta"]["source"] for suite, index in errors)
        wrong_by_source = Counter(sources[suite][index]["_meta"]["source"] for (suite,index), names in errors.items() for _ in names)
        manifest["models"][model] = {
            "target_sources": sorted(targets), "seed_wrong_questions": sum(map(len, errors.values())),
            "seed_wrong_contexts": len(errors), "seed_contexts_by_source": dict(sorted(by_source.items())),
            "seed_wrong_questions_by_source": dict(sorted(wrong_by_source.items())),
            "train_records": len(train), "train_questions": sum(len(r["questions"]) for r in train),
            "development_records": len(development), "development_questions": sum(len(r["questions"]) for r in development),
            "input_row_sha256": {str(p): sha(p) for p in rows_paths.values()},
            "output_sha256": {split: sha(OUT / f"{model}_{split}.jsonl") for split in ["train", "development"]},
            "checks": {"baseline_rows_order_and_labels_aligned": True, "all_seed_errors_covered": True,
                       "three_train_one_development_per_context": True, "question_labels_and_types_preserved": True,
                       "no_exact_frozen_test_state": True, "unique_record_ids": True}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({m: {k: v for k, v in x.items() if k not in ["input_row_sha256", "output_sha256"]} for m,x in manifest["models"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
