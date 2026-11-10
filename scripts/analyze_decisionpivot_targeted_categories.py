#!/usr/bin/env python3
"""Pair DecisionPivot predictions across Kev checkpoints for the 45 targeted slices."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


Predicate = Callable[[dict[str, Any]], bool]


def meta_eq(key: str, value: Any) -> Predicate:
    return lambda item: item.get("meta", {}).get(key) == value


CATEGORY_RULES: dict[str, tuple[str, Predicate, int]] = {
    "ledger_batch_total_error": ("ledger_reconcile", meta_eq("deviation", "batch_total"), 23),
    "log_actual_statement": ("log_count_check", meta_eq("deviation", "none"), 300),
    "state_equality_failure": ("state_goal", meta_eq("failed_type", "same"), 28),
    "record_derived_field": ("record_rule", meta_eq("deviation", "derived"), 40),
    "facts_multitable_subtraction": ("answerable_facts", meta_eq("form", "agg_subs"), 40),
    "dependency_complex_closure": ("dep_resolve", meta_eq("level", 3), 200),
    "policy_rule_precedence": ("policy_case", meta_eq("needs", "precedence"), 200),
    "dependency_version_conflict": ("dep_resolve", meta_eq("pair_kind", "conflict"), 40),
    "record_field_scope": ("record_rule", meta_eq("deviation", "dep_range"), 40),
    "log_both_boundaries": ("log_count_check", meta_eq("rule_for_end_times", "both"), 240),
    "dependency_exclusive_boundary": ("dep_resolve", meta_eq("bound_form", "excluded"), 56),
    "state_missing_step": ("state_goal", meta_eq("deviation", "step_missing"), 75),
    "dependency_missing_item": ("dep_resolve", meta_eq("pair_kind", "missing"), 156),
    "permission_three_level_tree": ("perm_inherit", meta_eq("tree_steps", 3), 70),
    "policy_four_exceptions": ("policy_case", meta_eq("exceptions", 4), 107),
    "permission_role_chain": ("perm_inherit", meta_eq("deviation", "role_chain"), 34),
    "dependency_self_constraint": ("dep_resolve", meta_eq("pair_kind", "own_req"), 156),
    "triage_category_priority": ("triage_order", meta_eq("deviation", "class"), 99),
    "state_wrong_object": ("state_goal", meta_eq("deviation", "wrong_target"), 75),
    "dependency_runtime": ("dep_resolve", meta_eq("pair_kind", "runtime"), 90),
    "facts_four_hop": ("answerable_facts", meta_eq("level", 3), 200),
    "permission_level2": ("perm_inherit", meta_eq("level", 2), 200),
    "state_step_order": ("state_goal", meta_eq("deviation", "steps_swapped"), 75),
    "permission_level3": ("perm_inherit", meta_eq("level", 3), 200),
    "facts_two_level_inheritance": ("answerable_facts", meta_eq("form", "inherit_chain2"), 80),
    "dependency_ordinary_boundary": ("dep_resolve", meta_eq("pair_kind", "bound"), 158),
    "state_quantity_failure": ("state_goal", meta_eq("failed_type", "count"), 86),
    "facts_inheritance_reasoning": ("answerable_facts", meta_eq("form", "inherit_rel"), 80),
    "permission_scope_change": ("perm_inherit", meta_eq("deviation", "scope"), 66),
    "permission_action_change": ("perm_inherit", meta_eq("deviation", "action"), 67),
    "schedule_equipment": ("sched_conflict", meta_eq("pair_deviation", "equipment"), 30),
    "log_off_by_one": ("log_count_check", meta_eq("deviation", "off_by_one"), 75),
    "ledger_missing_entry": ("ledger_reconcile", meta_eq("deviation", "missing"), 142),
    "clause_outside_condition": ("clause_change", meta_eq("case", "outside"), 167),
    "state_content_failure": ("state_goal", meta_eq("failed_type", "content"), 179),
    "policy_exception_handling": ("policy_case", meta_eq("needs", "exception"), 200),
    "ledger_fee_error": ("ledger_reconcile", meta_eq("deviation", "fee"), 24),
    "clause_level3": ("clause_change", meta_eq("level", 3), 200),
    "permission_sealed_resource": ("perm_inherit", meta_eq("deviation", "sealed"), 33),
    "filter_k_of_n": ("filter_match", meta_eq("planted_kind", "certs_k_of_n"), 42),
    "ledger_date_error": ("ledger_reconcile", meta_eq("deviation", "date"), 57),
    "schedule_capacity": ("sched_conflict", meta_eq("pair_deviation", "seats"), 96),
    "filter_conditional_rule": ("filter_match", meta_eq("planted_kind", "conditional"), 42),
    "schedule_level3": ("sched_conflict", meta_eq("level", 3), 200),
    "filter_converted_minimum": ("filter_match", meta_eq("planted_kind", "conv_min"), 42),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_items(data_root: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        task_dir.name: read_jsonl(task_dir / "items.jsonl")
        for task_dir in sorted((data_root / "tasks").iterdir())
        if (task_dir / "items.jsonl").exists()
    }


def load_choices(run_root: Path) -> dict[str, str]:
    choices: dict[str, str] = {}
    for path in sorted(run_root.glob("*.jsonl")):
        for row in read_jsonl(path):
            choices[row["id"]] = row["answers"]["q"]["choice"]
    return choices


def direction(delta: float) -> str:
    if delta > 1e-12:
        return "up"
    if delta < -1e-12:
        return "down"
    return "flat"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def pp(value: float) -> str:
    return f"{value * 100:+.2f}"


def mcnemar_exact(fixed: int, broken: int) -> float:
    """Two-sided exact McNemar p-value from discordant paired outcomes."""
    n = fixed + broken
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(fixed, broken) + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def bh_adjust(pvalues: list[float]) -> list[float]:
    order = sorted(range(len(pvalues)), key=pvalues.__getitem__)
    adjusted = [1.0] * len(pvalues)
    running = 1.0
    for reverse_rank, index in enumerate(reversed(order), 1):
        rank = len(pvalues) - reverse_rank + 1
        running = min(running, pvalues[index] * len(pvalues) / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--v1-run", type=Path, required=True)
    parser.add_argument("--full-run", type=Path, required=True)
    parser.add_argument("--blend-run", type=Path, required=True)
    parser.add_argument("--pivot-spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    # Import the project's canonical target counts and Chinese labels.
    import importlib.util

    module_spec = importlib.util.spec_from_file_location("pivot_spec", args.pivot_spec)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not import {args.pivot_spec}")
    pivot_spec = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = pivot_spec
    module_spec.loader.exec_module(pivot_spec)

    items_by_family = load_items(args.data_root)
    runs = {
        "v1": load_choices(args.v1_run),
        "full": load_choices(args.full_run),
        "blend": load_choices(args.blend_run),
    }
    all_items = [item for items in items_by_family.values() for item in items]
    ids = {item["id"] for item in all_items}
    if len(all_items) != 7800 or len(ids) != 7800:
        raise RuntimeError(f"Expected 7,800 unique items, got {len(all_items)} / {len(ids)}")
    for name, choices in runs.items():
        if set(choices) != ids:
            missing = ids - set(choices)
            extra = set(choices) - ids
            raise RuntimeError(f"{name} coverage mismatch: missing={len(missing)} extra={len(extra)}")

    spec_by_id = {spec.category_id: spec for spec in pivot_spec.CATEGORIES}
    rows: list[dict[str, Any]] = []
    category_members: dict[str, set[str]] = {}
    for rank, category_id in enumerate(CATEGORY_RULES, 1):
        family, predicate, expected_n = CATEGORY_RULES[category_id]
        members = [item for item in items_by_family[family] if predicate(item)]
        if len(members) != expected_n:
            raise RuntimeError(f"{category_id}: expected n={expected_n}, got {len(members)}")
        category_members[category_id] = {item["id"] for item in members}
        result: dict[str, Any] = {
            "rank": rank,
            "category_id": category_id,
            "name_zh": spec_by_id[category_id].name_zh,
            "family": family,
            "eval_n": len(members),
            "generated_n": spec_by_id[category_id].target,
        }
        for name, choices in runs.items():
            correct = sum(choices[item["id"]] == item["gold"] for item in members)
            result[f"{name}_correct"] = correct
            result[f"{name}_accuracy"] = correct / len(members)
        v1_flags = {item["id"]: runs["v1"][item["id"]] == item["gold"] for item in members}
        for candidate in ("full", "blend"):
            candidate_flags = {
                item["id"]: runs[candidate][item["id"]] == item["gold"] for item in members
            }
            fixed = sum(not v1_flags[item_id] and candidate_flags[item_id] for item_id in v1_flags)
            broken = sum(v1_flags[item_id] and not candidate_flags[item_id] for item_id in v1_flags)
            result[f"{candidate}_fixed_vs_v1"] = fixed
            result[f"{candidate}_broken_vs_v1"] = broken
            result[f"{candidate}_mcnemar_p_vs_v1"] = mcnemar_exact(fixed, broken)
        result["full_minus_v1"] = result["full_accuracy"] - result["v1_accuracy"]
        result["blend_minus_v1"] = result["blend_accuracy"] - result["v1_accuracy"]
        result["blend_minus_full"] = result["blend_accuracy"] - result["full_accuracy"]
        result["full_direction"] = direction(result["full_minus_v1"])
        result["blend_direction"] = direction(result["blend_minus_v1"])
        rows.append(result)

    for candidate in ("full", "blend"):
        adjusted = bh_adjust([row[f"{candidate}_mcnemar_p_vs_v1"] for row in rows])
        for row, value in zip(rows, adjusted):
            row[f"{candidate}_mcnemar_bh_q_vs_v1"] = value

    family_rows: list[dict[str, Any]] = []
    for family, members in sorted(items_by_family.items()):
        result = {"family": family, "eval_n": len(members)}
        for name, choices in runs.items():
            correct = sum(choices[item["id"]] == item["gold"] for item in members)
            result[f"{name}_correct"] = correct
            result[f"{name}_accuracy"] = correct / len(members)
        result["full_minus_v1"] = result["full_accuracy"] - result["v1_accuracy"]
        result["blend_minus_v1"] = result["blend_accuracy"] - result["v1_accuracy"]
        result["blend_minus_full"] = result["blend_accuracy"] - result["full_accuracy"]
        family_rows.append(result)

    targeted = [row for row in rows if row["generated_n"] > 0]
    untargeted = [row for row in rows if row["generated_n"] == 0]
    summary = {
        "coverage": {"items": 7800, "runs": {name: len(run) for name, run in runs.items()}},
        "targeted_categories": len(targeted),
        "zero_generated_categories": [row["category_id"] for row in untargeted],
        "targeted_v1_to_full": {
            label: sum(row["full_direction"] == label for row in targeted)
            for label in ("up", "flat", "down")
        },
        "targeted_v1_to_blend": {
            label: sum(row["blend_direction"] == label for row in targeted)
            for label in ("up", "flat", "down")
        },
        "all45_v1_to_full": {
            label: sum(row["full_direction"] == label for row in rows)
            for label in ("up", "flat", "down")
        },
        "all45_v1_to_blend": {
            label: sum(row["blend_direction"] == label for row in rows)
            for label in ("up", "flat", "down")
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "targeted_category_results.json").open("w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "categories": rows, "families": family_rows}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with (args.output_dir / "targeted_category_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    md: list[str] = [
        "# DecisionPivot 定向细类逐题配对结果",
        "",
        f"- 43 个实际生成细类，v1→全参：{summary['targeted_v1_to_full']}",
        f"- 43 个实际生成细类，v1→融合：{summary['targeted_v1_to_blend']}",
        "- 细类允许重叠，不能把各行 n 相加当作独立题数。",
        "",
        "## 任务族（逐题准确率）",
        "",
        "| 任务族 | n | v1 | 全参 | 融合 | 全参−v1 (pp) | 融合−v1 (pp) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in family_rows:
        md.append(
            f"| {row['family']} | {row['eval_n']} | {pct(row['v1_accuracy'])} | "
            f"{pct(row['full_accuracy'])} | {pct(row['blend_accuracy'])} | "
            f"{pp(row['full_minus_v1'])} | {pp(row['blend_minus_v1'])} |"
        )
    md.extend([
        "",
        "## 45 个细类",
        "",
        "| 排名 | 细类 | 生成量 | 评测 n | v1 | 全参 | 融合 | 全参−v1 (pp) | 融合−v1 (pp) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        md.append(
            f"| {row['rank']} | {row['name_zh']} | {row['generated_n']} | {row['eval_n']} | "
            f"{pct(row['v1_accuracy'])} | {pct(row['full_accuracy'])} | {pct(row['blend_accuracy'])} | "
            f"{pp(row['full_minus_v1'])} | {pp(row['blend_minus_v1'])} |"
        )
    (args.output_dir / "targeted_category_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
