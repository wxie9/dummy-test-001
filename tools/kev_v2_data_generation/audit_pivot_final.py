#!/usr/bin/env python3
"""Final cross-layer audit for the Pivot 20K structured and rendered datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import read_jsonl, validate_record  # noqa: E402
from pivot_generators import validate_structured  # noqa: E402
from pivot_spec import TARGETS, total_target  # noqa: E402


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structured", type=Path, required=True)
    parser.add_argument("--rendered", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    structured = read_jsonl(args.structured)
    rendered = read_jsonl(args.rendered)
    structured_by_hash = {row["_meta"]["state_sha256"]: row for row in structured}
    structured_ids = {row["id"] for row in structured}
    rendered_structured_hashes = [row.get("_meta", {}).get("structured_state_sha256") for row in rendered]

    structured_problems: List[Dict[str, Any]] = []
    for row in structured:
        problems = validate_structured(row)
        if problems:
            structured_problems.append({"id": row.get("id"), "problems": problems})
    rendered_problems: List[Dict[str, Any]] = []
    semantic_mismatches: List[Dict[str, Any]] = []
    context_lengths: List[int] = []
    label_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    category_answers: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rendered:
        problems = validate_record(row)
        if problems:
            rendered_problems.append({"id": row.get("_meta", {}).get("id"), "problems": problems})
        meta = row["_meta"]
        source = structured_by_hash.get(meta.get("structured_state_sha256"))
        question = row["questions"]["decision"]
        if source is None:
            semantic_mismatches.append({"id": meta.get("id"), "problem": "structured_hash_not_found"})
        else:
            expected_label = source["question_spec"]["label"]
            if question.get("label") != expected_label:
                semantic_mismatches.append({"id": meta.get("id"), "problem": "label_changed", "expected": expected_label, "actual": question.get("label")})
            if set(question.get("criteria", {})) != set(source["question_spec"]["semantic_options"]):
                semantic_mismatches.append({"id": meta.get("id"), "problem": "option_keys_changed"})
            category_answers[source["category_id"]][str(source["solver"]["answer"])] += 1
        category_counts[meta["pivot_category_id"]] += 1
        family_counts[meta["family"]] += 1
        label_counts[question["label"]] += 1
        context_lengths.append(len(row["state"]["context"]))

    target_nonzero = {key: value for key, value in TARGETS.items() if value}
    category_count_mismatches = {
        key: {"expected": value, "actual": category_counts.get(key, 0)}
        for key, value in target_nonzero.items()
        if category_counts.get(key, 0) != value
    }
    unexpected_categories = sorted(set(category_counts) - set(target_nonzero))
    answer_max_ratio = {
        category: max(counts.values()) / sum(counts.values())
        for category, counts in category_answers.items()
    }
    duplicate_counts = {
        "structured_ids": len(structured) - len(structured_ids),
        "structured_state_hashes": len(structured) - len(structured_by_hash),
        "rendered_ids": len(rendered) - len({row["_meta"]["id"] for row in rendered}),
        "rendered_state_hashes": len(rendered) - len({row["_meta"]["state_sha256"] for row in rendered}),
        "rendered_structured_hashes": len(rendered_structured_hashes) - len(set(rendered_structured_hashes)),
    }
    passed = (
        len(structured) == total_target()
        and len(rendered) == total_target()
        and not structured_problems
        and not rendered_problems
        and not semantic_mismatches
        and not category_count_mismatches
        and not unexpected_categories
        and all(value == 0 for value in duplicate_counts.values())
    )
    result = {
        "passed": passed,
        "structured": {"path": str(args.structured), "records": len(structured), "sha256": file_sha256(args.structured)},
        "rendered": {"path": str(args.rendered), "records": len(rendered), "sha256": file_sha256(args.rendered)},
        "coverage": {
            "configured_categories": len(TARGETS),
            "nonzero_categories": len(target_nonzero),
            "rendered_categories": len(category_counts),
            "category_counts": dict(sorted(category_counts.items())),
            "family_counts": dict(sorted(family_counts.items())),
            "category_count_mismatches": category_count_mismatches,
            "unexpected_categories": unexpected_categories,
        },
        "quality": {
            "duplicate_counts": duplicate_counts,
            "structured_validation_failures": len(structured_problems),
            "rendered_validation_failures": len(rendered_problems),
            "cross_layer_semantic_mismatches": len(semantic_mismatches),
            "label_position_counts": dict(sorted(label_counts.items())),
            "maximum_single_answer_ratio_across_categories": max(answer_max_ratio.values()),
            "context_characters": {
                "min": min(context_lengths),
                "median": statistics.median(context_lengths),
                "mean": statistics.mean(context_lengths),
                "max": max(context_lengths),
            },
        },
        "boundaries": [
            "Independent targeted reconstruction; not official Kev v2 private rows.",
            "DecisionPivot taxonomy informed allocation, so later DecisionPivot gains are targeted-repair evidence, not independent generalization evidence.",
            "LLM fidelity review reduces but does not eliminate semantic-rendering risk; human sampling remains required before training.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "structured": len(structured), "rendered": len(rendered), "out": str(args.out)}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
