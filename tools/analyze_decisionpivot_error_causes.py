#!/usr/bin/env python3
"""Reproducible DecisionPivot error-cause audit for Kev blend vs StartLux.

The script deliberately separates exact, mutually exclusive decompositions from
overlapping diagnostic slices.  It writes machine-readable CSV/JSON outputs;
the narrative report is authored separately from these checked tables.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


MODELS = ("kev_blend", "startlux_instant", "startlux_autothink")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.fmean(vals) if vals else float("nan")


def safe_median(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.median(vals) if vals else float("nan")


def top_margin(probs: dict[str, float]) -> float:
    vals = sorted((float(value) for value in probs.values()), reverse=True)
    return vals[0] - vals[1] if len(vals) >= 2 else vals[0]


def ece(rows: list[dict[str, Any]], bins: int = 10) -> float:
    total = len(rows)
    out = 0.0
    for index in range(bins):
        lo, hi = index / bins, (index + 1) / bins
        selected = [
            row
            for row in rows
            if lo <= row["pmax"] <= hi
            and (index == bins - 1 or row["pmax"] < hi)
        ]
        if selected:
            accuracy = safe_mean(float(row["correct"]) for row in selected)
            confidence = safe_mean(row["pmax"] for row in selected)
            out += len(selected) / total * abs(accuracy - confidence)
    return out


def normalize_meta_value(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


META_FIELDS = {
    "answerable_facts": ["level", "form", "missing_role", "hops", "deviation"],
    "perm_inherit": [
        "level",
        "sub",
        "variant",
        "deviation",
        "tree_steps",
        "inclusion_steps",
        "membership_links",
    ],
    "policy_case": ["level", "precedence", "near_threshold", "needs", "default"],
    "log_count_check": ["level", "rule_for_end_times", "deviation"],
    "sched_conflict": ["level", "pair_deviation", "field", "variant", "deviation"],
    "state_goal": ["level", "failed_type", "deviation"],
    "toolcall_valid": [
        "level",
        "deviation_where",
        "deviation",
        "deviation_detail",
    ],
    "triage_order": ["level", "position_asked", "change", "combine", "variant"],
    "clause_change": ["level", "deviation", "topic_role", "polarity"],
    "dep_resolve": [
        "level",
        "pair_kind",
        "bound_form",
        "trap",
        "conflict_sub",
        "deviation",
    ],
    "ledger_reconcile": ["level", "deviation", "group_type"],
    "record_rule": ["level", "violated_kind", "deviation", "variant"],
    "filter_match": [
        "level",
        "planted_kind",
        "limit_wording",
        "deviation",
        "pattern",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--items-root", type=Path, required=True)
    parser.add_argument("--targeted-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    predictions = read_jsonl(args.predictions)
    by_item: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in predictions:
        key = row["item_id"]
        model = row["model"]
        if model in by_item[key]:
            raise ValueError(f"duplicate model prediction: {key} {model}")
        by_item[key][model] = row

    items: dict[str, dict[str, Any]] = {}
    for path in sorted(args.items_root.glob("*/items.jsonl")):
        for item in read_jsonl(path):
            if item["id"] in items:
                raise ValueError(f"duplicate item id: {item['id']}")
            items[item["id"]] = item

    if set(items) != set(by_item):
        missing_pred = sorted(set(items) - set(by_item))
        missing_item = sorted(set(by_item) - set(items))
        raise ValueError(
            f"alignment mismatch missing_pred={len(missing_pred)} "
            f"missing_item={len(missing_item)}"
        )

    joined: list[dict[str, Any]] = []
    for item_id in sorted(items):
        item = items[item_id]
        model_rows = by_item[item_id]
        if set(model_rows) != set(MODELS):
            raise ValueError(f"incomplete models for {item_id}: {sorted(model_rows)}")
        gold = str(item["gold"])
        task = model_rows["kev_blend"]["task"]
        if any(model_rows[model]["task"] != task for model in MODELS):
            raise ValueError(f"task mismatch for {item_id}")
        row: dict[str, Any] = {
            "item_id": item_id,
            "task": task,
            "gold": gold,
            "meta": item.get("meta") or {},
        }
        for model in MODELS:
            pred = model_rows[model]
            probs = {str(key): float(value) for key, value in pred["probabilities"].items()}
            choice = str(pred["choice"])
            if choice not in probs:
                raise ValueError(f"choice absent from probabilities: {item_id} {model}")
            if gold not in probs:
                raise ValueError(f"gold absent from probabilities: {item_id} {model}")
            if any(value < 0.0 or value > 1.0 for value in probs.values()):
                raise ValueError(f"probability out of range: {item_id} {model}")
            if not math.isclose(sum(probs.values()), 1.0, rel_tol=0.0, abs_tol=2e-3):
                raise ValueError(
                    f"probabilities do not sum to one: {item_id} {model} "
                    f"sum={sum(probs.values())}"
                )
            row[model] = {
                "choice": choice,
                "correct": choice == gold,
                "probs": probs,
                "pmax": max(probs.values()),
                "p_gold": probs[gold],
                "margin": top_margin(probs),
                "confidence": float(pred["confidence"]),
                "none_probability": pred.get("none_probability"),
            }
        joined.append(row)

    if len(joined) != 7800:
        raise ValueError(f"expected 7800 aligned items, got {len(joined)}")

    # Exact family-level partition.
    family_rows: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in joined}):
        subset = [row for row in joined if row["task"] == task]
        errors = [row for row in subset if not row["kev_blend"]["correct"]]
        buckets = Counter()
        for row in errors:
            inst = row["startlux_instant"]["correct"]
            auto = row["startlux_autothink"]["correct"]
            if inst and auto:
                buckets["both_sl_correct"] += 1
            elif inst:
                buckets["instant_only_correct"] += 1
            elif auto:
                buckets["autothink_only_correct"] += 1
            else:
                buckets["neither_sl_correct"] += 1
        family_rows.append(
            {
                "task": task,
                "n": len(subset),
                "kev_correct": len(subset) - len(errors),
                "kev_accuracy": (len(subset) - len(errors)) / len(subset),
                "kev_errors": len(errors),
                "error_rate": len(errors) / len(subset),
                "share_of_all_kev_errors": len(errors)
                / sum(not row["kev_blend"]["correct"] for row in joined),
                "both_sl_correct": buckets["both_sl_correct"],
                "instant_only_correct": buckets["instant_only_correct"],
                "autothink_only_correct": buckets["autothink_only_correct"],
                "neither_sl_correct": buckets["neither_sl_correct"],
                "wrong_pmax_mean": safe_mean(row["kev_blend"]["pmax"] for row in errors),
                "wrong_p_gold_mean": safe_mean(row["kev_blend"]["p_gold"] for row in errors),
                "wrong_margin_mean": safe_mean(row["kev_blend"]["margin"] for row in errors),
                "wrong_pmax_ge_0_8": sum(row["kev_blend"]["pmax"] >= 0.8 for row in errors),
                "wrong_pmax_ge_0_9": sum(row["kev_blend"]["pmax"] >= 0.9 for row in errors),
                "wrong_pmax_ge_0_95": sum(row["kev_blend"]["pmax"] >= 0.95 for row in errors),
            }
        )
    family_fields = list(family_rows[0])
    write_csv(args.output / "family_error_decomposition.csv", family_rows, family_fields)

    # Exact model-comparison buckets over all Kev errors.
    comparison = Counter()
    for row in joined:
        if row["kev_blend"]["correct"]:
            continue
        inst = row["startlux_instant"]["correct"]
        auto = row["startlux_autothink"]["correct"]
        if inst and auto:
            comparison["both_sl_correct"] += 1
        elif inst:
            comparison["instant_only_correct"] += 1
        elif auto:
            comparison["autothink_only_correct"] += 1
        else:
            comparison["neither_sl_correct"] += 1

    # Model calibration/uncertainty summary.
    model_summary: list[dict[str, Any]] = []
    for model in MODELS:
        flat = []
        for row in joined:
            current = dict(row[model])
            current["correct"] = bool(current["correct"])
            flat.append(current)
        correct = [row for row in flat if row["correct"]]
        wrong = [row for row in flat if not row["correct"]]
        nll = safe_mean(-math.log(max(row["p_gold"], 1e-12)) for row in flat)
        brier = safe_mean(
            sum(
                (prob - (1.0 if option == joined[index]["gold"] else 0.0)) ** 2
                for option, prob in row["probs"].items()
            )
            for index, row in enumerate(flat)
        )
        model_summary.append(
            {
                "model": model,
                "n": len(flat),
                "correct": len(correct),
                "accuracy": len(correct) / len(flat),
                "pmax_mean": safe_mean(row["pmax"] for row in flat),
                "calibration_bias_pmax_minus_accuracy": safe_mean(
                    row["pmax"] for row in flat
                )
                - len(correct) / len(flat),
                "pmax_correct_mean": safe_mean(row["pmax"] for row in correct),
                "pmax_wrong_mean": safe_mean(row["pmax"] for row in wrong),
                "pmax_wrong_median": safe_median(row["pmax"] for row in wrong),
                "p_gold_mean": safe_mean(row["p_gold"] for row in flat),
                "nll": nll,
                "brier": brier,
                "ece_10": ece(flat),
                "wrong_pmax_ge_0_8": sum(row["pmax"] >= 0.8 for row in wrong),
                "wrong_pmax_ge_0_9": sum(row["pmax"] >= 0.9 for row in wrong),
                "wrong_pmax_ge_0_95": sum(row["pmax"] >= 0.95 for row in wrong),
            }
        )
    write_csv(args.output / "model_calibration_summary.csv", model_summary, list(model_summary[0]))

    # Binary yes/no directional bias.  This is a partition within each included family.
    binary_rows: list[dict[str, Any]] = []
    for task in sorted({row["task"] for row in joined}):
        subset = [row for row in joined if row["task"] == task]
        labels = {row["gold"] for row in subset}
        choices = {row["kev_blend"]["choice"] for row in subset}
        if labels <= {"yes", "no"} and choices <= {"yes", "no"}:
            for gold in ("yes", "no"):
                gold_rows = [row for row in subset if row["gold"] == gold]
                binary_rows.append(
                    {
                        "task": task,
                        "gold": gold,
                        "n": len(gold_rows),
                        "correct": sum(row["kev_blend"]["correct"] for row in gold_rows),
                        "accuracy": safe_mean(row["kev_blend"]["correct"] for row in gold_rows),
                        "pred_yes": sum(row["kev_blend"]["choice"] == "yes" for row in gold_rows),
                        "pred_no": sum(row["kev_blend"]["choice"] == "no" for row in gold_rows),
                    }
                )
    if binary_rows:
        write_csv(args.output / "binary_label_bias.csv", binary_rows, list(binary_rows[0]))

    # Metadata subgroup scan.  These rows are diagnostic and can overlap.
    meta_rows: list[dict[str, Any]] = []
    for task, fields in META_FIELDS.items():
        task_rows = [row for row in joined if row["task"] == task]
        task_error_rate = safe_mean(not row["kev_blend"]["correct"] for row in task_rows)
        for field in fields:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in task_rows:
                groups[normalize_meta_value(row["meta"].get(field))].append(row)
            for value, group in groups.items():
                if len(group) < 20:
                    continue
                errors = sum(not row["kev_blend"]["correct"] for row in group)
                rate = errors / len(group)
                meta_rows.append(
                    {
                        "task": task,
                        "field": field,
                        "value": value,
                        "n": len(group),
                        "errors": errors,
                        "error_rate": rate,
                        "task_error_rate": task_error_rate,
                        "excess_error_rate": rate - task_error_rate,
                        "excess_error_count_vs_task_rate": len(group) * (rate - task_error_rate),
                    }
                )
    meta_rows.sort(
        key=lambda row: (row["excess_error_count_vs_task_rate"], row["errors"]), reverse=True
    )
    if meta_rows:
        write_csv(args.output / "metadata_subgroup_scan.csv", meta_rows, list(meta_rows[0]))

    # Benchmark level is an exact 3-way partition: 200 examples per level per family.
    level_rows: list[dict[str, Any]] = []
    for level in (1, 2, 3):
        subset = [row for row in joined if row["meta"].get("level") == level]
        errors = sum(not row["kev_blend"]["correct"] for row in subset)
        level_rows.append(
            {
                "level": level,
                "n": len(subset),
                "correct": len(subset) - errors,
                "accuracy": (len(subset) - errors) / len(subset),
                "errors": errors,
                "error_rate": errors / len(subset),
                "share_of_all_kev_errors": errors
                / sum(not row["kev_blend"]["correct"] for row in joined),
            }
        )
    write_csv(args.output / "level_error_decomposition.csv", level_rows, list(level_rows[0]))

    # Existing 45 predeclared weakness slices. They overlap and are not additive.
    with args.targeted_csv.open(encoding="utf-8", newline="") as handle:
        targeted = list(csv.DictReader(handle))
    slice_rows: list[dict[str, Any]] = []
    for row in targeted:
        n = int(row["eval_n"])
        correct = int(row["blend_correct"])
        slice_rows.append(
            {
                "rank": int(row["rank"]),
                "category_id": row["category_id"],
                "name_zh": row["name_zh"],
                "family": row["family"],
                "n": n,
                "correct": correct,
                "errors": n - correct,
                "accuracy": correct / n,
                "error_rate": (n - correct) / n,
                "blend_minus_v1": float(row["blend_minus_v1"]),
                "generated_n": int(row["generated_n"]),
            }
        )
    write_csv(args.output / "weakness_slice_error_stats.csv", slice_rows, list(slice_rows[0]))

    error_examples: list[dict[str, Any]] = []
    for row in joined:
        kev = row["kev_blend"]
        if kev["correct"]:
            continue
        inst = row["startlux_instant"]
        auto = row["startlux_autothink"]
        if inst["correct"] and auto["correct"]:
            bucket = "both_sl_correct"
        elif inst["correct"]:
            bucket = "instant_only_correct"
        elif auto["correct"]:
            bucket = "autothink_only_correct"
        else:
            bucket = "neither_sl_correct"
        error_examples.append(
            {
                "item_id": row["item_id"],
                "task": row["task"],
                "gold": row["gold"],
                "kev_choice": kev["choice"],
                "kev_pmax": kev["pmax"],
                "kev_p_gold": kev["p_gold"],
                "kev_margin": kev["margin"],
                "startlux_instant_choice": inst["choice"],
                "startlux_instant_correct": inst["correct"],
                "startlux_autothink_choice": auto["choice"],
                "startlux_autothink_correct": auto["correct"],
                "comparison_bucket": bucket,
            }
        )
    error_examples.sort(key=lambda row: (row["kev_pmax"], -row["kev_p_gold"]), reverse=True)
    write_csv(args.output / "kev_error_rows.csv", error_examples, list(error_examples[0]))

    summary = {
        "scope": {
            "items": len(joined),
            "tasks": len({row["task"] for row in joined}),
            "models": list(MODELS),
            "kev_correct": sum(row["kev_blend"]["correct"] for row in joined),
            "kev_errors": sum(not row["kev_blend"]["correct"] for row in joined),
        },
        "kev_error_comparison_buckets": dict(comparison),
        "checks": {
            "prediction_records": len(predictions),
            "aligned_items": len(joined),
            "records_per_model": {
                model: sum(1 for row in predictions if row["model"] == model)
                for model in MODELS
            },
            "family_n_sum": sum(row["n"] for row in family_rows),
            "family_error_sum": sum(row["kev_errors"] for row in family_rows),
            "comparison_bucket_sum": sum(comparison.values()),
            "level_n_sum": sum(row["n"] for row in level_rows),
            "level_error_sum": sum(row["errors"] for row in level_rows),
            "weakness_slice_count": len(slice_rows),
            "weakness_slice_n_sum_nonadditive": sum(row["n"] for row in slice_rows),
        },
        "notes": [
            "Family rows and StartLux comparison buckets are mutually exclusive and additive.",
            "Metadata subgroups and 45 weakness slices overlap; their counts must not be summed.",
            "Calibration uses the exported option probabilities, not the derived confidence field.",
        ],
    }
    with (args.output / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
