#!/usr/bin/env python3
"""Audit DecisionPivot errors using the user-defined large-error rule.

A wrong item is a large error when either:
1. the gold answer is not ranked second; or
2. the gold answer is ranked second and p(top1) - p(gold) > 0.30.

The script keeps exact partitions separate from overlapping fine-category and
metadata slices.  It does not infer hidden chain-of-thought or causal training
effects.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


META_FIELDS = {
    "answerable_facts": ["level", "form", "missing_role", "hops", "deviation"],
    "perm_inherit": [
        "level", "sub", "variant", "deviation", "tree_steps",
        "inclusion_steps", "membership_links",
    ],
    "policy_case": ["level", "precedence", "near_threshold", "needs", "default"],
    "log_count_check": ["level", "rule_for_end_times", "deviation"],
    "sched_conflict": ["level", "pair_deviation", "field", "variant", "deviation"],
    "state_goal": ["level", "failed_type", "deviation"],
    "toolcall_valid": ["level", "deviation_where", "deviation", "deviation_detail"],
    "triage_order": ["level", "position_asked", "change", "combine", "variant"],
    "clause_change": ["level", "deviation", "topic_role", "polarity"],
    "dep_resolve": ["level", "pair_kind", "bound_form", "trap", "conflict_sub", "deviation"],
    "ledger_reconcile": ["level", "deviation", "group_type"],
    "record_rule": ["level", "violated_kind", "deviation", "variant"],
    "filter_match": ["level", "planted_kind", "limit_wording", "deviation", "pattern"],
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def norm(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--items-root", type=Path, required=True)
    parser.add_argument("--category-membership", type=Path, required=True)
    parser.add_argument("--category-profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    states = read_csv(args.states)
    if len(states) != 7800:
        raise ValueError(f"expected 7800 state rows, got {len(states)}")
    if len({row["item_id"] for row in states}) != 7800:
        raise ValueError("state item IDs are not unique")

    predictions: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_jsonl(args.predictions):
        predictions[row["item_id"]][row["model"]] = row
    if set(predictions) != {row["item_id"] for row in states}:
        raise ValueError("prediction/state item sets do not match")

    items: dict[str, dict[str, Any]] = {}
    for path in sorted(args.items_root.glob("*/items.jsonl")):
        for row in read_jsonl(path):
            if row["id"] in items:
                raise ValueError(f"duplicate item: {row['id']}")
            items[row["id"]] = row
    if set(items) != set(predictions):
        raise ValueError("item/prediction item sets do not match")

    joined: list[dict[str, Any]] = []
    for raw in states:
        row = dict(raw)
        row["correct"] = row["correct"] == "True"
        for key in ("level", "n_options", "gold_rank"):
            row[key] = int(float(row[key]))
        for key in ("chance", "p_gold", "pmax", "margin", "gold_gap"):
            row[key] = float(row[key])
        row["sl_instant_correct"] = row["sl_instant_correct"] == "True"
        row["sl_autothink_correct"] = row["sl_autothink_correct"] == "True"
        row["meta"] = items[row["item_id"]].get("meta") or {}
        row["item"] = items[row["item_id"]]
        row["predictions"] = predictions[row["item_id"]]
        if not row["correct"]:
            row["large_error"] = row["gold_rank"] != 2 or row["gold_gap"] > 0.30
            if row["large_error"]:
                if row["gold_rank"] != 2:
                    row["large_error_reason"] = "gold_rank_3plus"
                elif row["gold_gap"] <= 0.50:
                    row["large_error_reason"] = "rank2_gap_030_050"
                elif row["gold_gap"] <= 0.70:
                    row["large_error_reason"] = "rank2_gap_050_070"
                else:
                    row["large_error_reason"] = "rank2_gap_gt_070"
            else:
                row["large_error_reason"] = "small_error_rank2_gap_le_030"
        else:
            row["large_error"] = False
            row["large_error_reason"] = "correct"
        joined.append(row)

    wrong = [row for row in joined if not row["correct"]]
    large = [row for row in wrong if row["large_error"]]
    small = [row for row in wrong if not row["large_error"]]
    if len(wrong) != 2253 or len(large) != 1709 or len(small) != 544:
        raise ValueError(
            f"unexpected partition wrong={len(wrong)} large={len(large)} small={len(small)}"
        )

    exact_rows = []
    for row in large:
        pred = row["predictions"]["kev_blend"]
        exact_rows.append(
            {
                "item_id": row["item_id"],
                "task": row["task"],
                "level": row["level"],
                "gold": row["gold"],
                "choice": row["choice"],
                "n_options": row["n_options"],
                "gold_rank": row["gold_rank"],
                "p_gold": row["p_gold"],
                "pmax": row["pmax"],
                "gold_gap": row["gold_gap"],
                "large_error_reason": row["large_error_reason"],
                "sl_instant_correct": row["sl_instant_correct"],
                "sl_autothink_correct": row["sl_autothink_correct"],
                "kev_probabilities": json.dumps(pred["probabilities"], ensure_ascii=False, sort_keys=True),
                "metadata": json.dumps(row["meta"], ensure_ascii=False, sort_keys=True),
            }
        )
    exact_rows.sort(key=lambda r: (-r["gold_gap"], r["item_id"]))
    write_csv(args.output / "large_error_rows.csv", exact_rows)

    with (args.output / "large_error_questions.jsonl").open("w", encoding="utf-8") as handle:
        for row in sorted(large, key=lambda r: (-r["gold_gap"], r["item_id"])):
            handle.write(
                json.dumps(
                    {
                        "item_id": row["item_id"],
                        "task": row["task"],
                        "level": row["level"],
                        "gold": row["gold"],
                        "choice": row["choice"],
                        "gold_rank": row["gold_rank"],
                        "p_gold": row["p_gold"],
                        "pmax": row["pmax"],
                        "gold_gap": row["gold_gap"],
                        "large_error_reason": row["large_error_reason"],
                        "state": row["item"].get("state"),
                        "questions": row["item"].get("questions"),
                        "metadata": row["meta"],
                        "kev": row["predictions"]["kev_blend"],
                        "startlux_instant": row["predictions"]["startlux_instant"],
                        "startlux_autothink": row["predictions"]["startlux_autothink"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    family_rows = []
    for task in sorted({row["task"] for row in joined}):
        all_task = [row for row in joined if row["task"] == task]
        task_errors = [row for row in all_task if not row["correct"]]
        task_large = [row for row in task_errors if row["large_error"]]
        buckets = Counter(row["large_error_reason"] for row in task_large)
        sl = Counter()
        for row in task_large:
            if row["sl_instant_correct"] and row["sl_autothink_correct"]:
                sl["both"] += 1
            elif row["sl_instant_correct"]:
                sl["instant_only"] += 1
            elif row["sl_autothink_correct"]:
                sl["autothink_only"] += 1
            else:
                sl["neither"] += 1
        family_rows.append(
            {
                "task": task,
                "n": len(all_task),
                "errors": len(task_errors),
                "large_errors": len(task_large),
                "large_error_rate_all": len(task_large) / len(all_task),
                "large_share_of_errors": len(task_large) / len(task_errors),
                "share_of_all_large_errors": len(task_large) / len(large),
                "gold_rank_3plus": buckets["gold_rank_3plus"],
                "rank2_gap_gt_030": len(task_large) - buckets["gold_rank_3plus"],
                "sl_both_correct": sl["both"],
                "sl_instant_only_correct": sl["instant_only"],
                "sl_autothink_only_correct": sl["autothink_only"],
                "sl_neither_correct": sl["neither"],
            }
        )
    family_rows.sort(key=lambda r: (-r["large_errors"], r["task"]))
    write_csv(args.output / "family_large_error_profile.csv", family_rows)

    level_rows = []
    for level in (1, 2, 3):
        all_level = [row for row in joined if row["level"] == level]
        errors = [row for row in all_level if not row["correct"]]
        big = [row for row in errors if row["large_error"]]
        level_rows.append(
            {
                "level": level,
                "n": len(all_level),
                "errors": len(errors),
                "large_errors": len(big),
                "large_error_rate_all": len(big) / len(all_level),
                "large_share_of_errors": len(big) / len(errors),
                "share_of_all_large_errors": len(big) / len(large),
            }
        )
    write_csv(args.output / "level_large_error_profile.csv", level_rows)

    binary_rows = []
    for task in sorted({row["task"] for row in joined}):
        all_task = [row for row in joined if row["task"] == task]
        if {row["gold"] for row in all_task} <= {"yes", "no"}:
            for gold in ("yes", "no"):
                subset = [row for row in all_task if row["gold"] == gold]
                errors = [row for row in subset if not row["correct"]]
                big = [row for row in errors if row["large_error"]]
                binary_rows.append(
                    {
                        "task": task,
                        "gold": gold,
                        "n": len(subset),
                        "errors": len(errors),
                        "large_errors": len(big),
                        "large_error_rate_all": len(big) / len(subset),
                        "large_share_of_errors": len(big) / len(errors) if errors else 0.0,
                    }
                )
    write_csv(args.output / "binary_direction_large_errors.csv", binary_rows)

    memberships: dict[str, set[str]] = defaultdict(set)
    for row in read_csv(args.category_membership):
        memberships[row["category_id"]].add(row["item_id"])
    profile_names = {
        row["group_id"]: (row["name_zh"], row["family"])
        for row in read_csv(args.category_profiles)
    }
    category_rows = []
    for category_id in sorted(memberships):
        ids = memberships[category_id]
        subset = [row for row in joined if row["item_id"] in ids]
        errors = [row for row in subset if not row["correct"]]
        big = [row for row in errors if row["large_error"]]
        name, family = profile_names[category_id]
        category_rows.append(
            {
                "category_id": category_id,
                "name_zh": name,
                "family": family,
                "n": len(subset),
                "errors": len(errors),
                "large_errors": len(big),
                "large_error_rate_all": len(big) / len(subset),
                "large_share_of_errors": len(big) / len(errors) if errors else 0.0,
                "gold_rank_3plus": sum(row["gold_rank"] != 2 for row in big),
                "rank2_gap_gt_030": sum(row["gold_rank"] == 2 for row in big),
            }
        )
    category_rows.sort(key=lambda r: (-r["large_error_rate_all"], -r["large_errors"], r["category_id"]))
    write_csv(args.output / "category_large_error_profile.csv", category_rows)

    meta_rows = []
    for task, fields in META_FIELDS.items():
        task_rows = [row for row in joined if row["task"] == task]
        task_large_rate = sum(row["large_error"] for row in task_rows) / len(task_rows)
        for field in fields:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in task_rows:
                groups[norm(row["meta"].get(field))].append(row)
            for value, group in groups.items():
                if len(group) < 20:
                    continue
                errors = [row for row in group if not row["correct"]]
                big = [row for row in errors if row["large_error"]]
                rate = len(big) / len(group)
                meta_rows.append(
                    {
                        "task": task,
                        "field": field,
                        "value": value,
                        "n": len(group),
                        "errors": len(errors),
                        "large_errors": len(big),
                        "large_error_rate_all": rate,
                        "large_share_of_errors": len(big) / len(errors) if errors else 0.0,
                        "task_large_error_rate": task_large_rate,
                        "excess_large_error_rate": rate - task_large_rate,
                        "excess_large_error_count_vs_task_rate": (rate - task_large_rate) * len(group),
                    }
                )
    meta_rows.sort(
        key=lambda r: (-r["excess_large_error_count_vs_task_rate"], -r["large_errors"], r["task"])
    )
    write_csv(args.output / "metadata_large_error_scan.csv", meta_rows)

    # Preserve a small, inspectable set of representative source items.  For
    # each family select the two largest gold gaps, preferring distinct reasons.
    case_rows = []
    for task in sorted({row["task"] for row in large}):
        candidates = sorted(
            [row for row in large if row["task"] == task],
            key=lambda r: (-r["gold_gap"], -r["gold_rank"], r["item_id"]),
        )
        selected = []
        seen_reasons = set()
        for row in candidates:
            if row["large_error_reason"] not in seen_reasons or len(selected) == 0:
                selected.append(row)
                seen_reasons.add(row["large_error_reason"])
            if len(selected) == 2:
                break
        for row in candidates:
            if len(selected) == 2:
                break
            if row not in selected:
                selected.append(row)
        for row in selected:
            case_rows.append(
                {
                    "item_id": row["item_id"],
                    "task": task,
                    "level": row["level"],
                    "gold": row["gold"],
                    "choice": row["choice"],
                    "gold_rank": row["gold_rank"],
                    "p_gold": row["p_gold"],
                    "pmax": row["pmax"],
                    "gold_gap": row["gold_gap"],
                    "large_error_reason": row["large_error_reason"],
                    "metadata": row["meta"],
                    "questions": row["item"].get("questions"),
                    "state": row["item"].get("state"),
                    "kev_probabilities": row["predictions"]["kev_blend"]["probabilities"],
                    "startlux_instant": row["predictions"]["startlux_instant"],
                    "startlux_autothink": row["predictions"]["startlux_autothink"],
                }
            )
    with (args.output / "representative_large_error_cases.jsonl").open("w", encoding="utf-8") as handle:
        for row in case_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    reason_counts = Counter(row["large_error_reason"] for row in large)
    sl_counts = Counter()
    for row in large:
        if row["sl_instant_correct"] and row["sl_autothink_correct"]:
            sl_counts["both_correct"] += 1
        elif row["sl_instant_correct"]:
            sl_counts["instant_only_correct"] += 1
        elif row["sl_autothink_correct"]:
            sl_counts["autothink_only_correct"] += 1
        else:
            sl_counts["neither_correct"] += 1
    summary = {
        "definition": {
            "population": "wrong DecisionPivot items only",
            "large_error": "gold_rank != 2 OR (gold_rank == 2 AND pmax-p_gold > 0.30)",
            "small_error": "gold_rank == 2 AND pmax-p_gold <= 0.30",
        },
        "counts": {
            "all_items": len(joined),
            "wrong_items": len(wrong),
            "large_errors": len(large),
            "small_errors": len(small),
            "large_share_of_wrong": len(large) / len(wrong),
            "large_share_of_all": len(large) / len(joined),
            "large_error_reasons": dict(reason_counts),
            "startlux_on_large_errors": dict(sl_counts),
        },
        "checks": {
            "large_plus_small_equals_wrong": len(large) + len(small) == len(wrong),
            "family_large_sum": sum(row["large_errors"] for row in family_rows),
            "level_large_sum": sum(row["large_errors"] for row in level_rows),
            "representative_cases": len(case_rows),
            "fine_categories_are_overlapping": True,
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
