#!/usr/bin/env python3
"""Classify DecisionPivot outcomes by probability margin and mastery evidence.

This audit distinguishes stable correct answers, fragile correct answers,
near-miss errors, and confident errors.  "Fragile correct" is deliberately not
called a guess: a single probability vector cannot reveal the causal reasoning
process.  Category-level mastery labels are transparent heuristics relative to
the actual option-count chance rate.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float("nan")


def load_category_rules(path: Path) -> dict[str, tuple[str, Callable[[dict[str, Any]], bool], int]]:
    spec = importlib.util.spec_from_file_location("targeted_category_rules", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import category rules from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.CATEGORY_RULES


def classify_outcome(correct: bool, margin: float, gold_rank: int, gold_gap: float, pmax: float, p_gold: float) -> str:
    if correct:
        if margin < 0.10:
            return "fragile_correct"
        if margin < 0.50:
            return "moderate_correct"
        return "stable_correct"
    if gold_rank == 2 and gold_gap < 0.10:
        return "near_miss_wrong"
    if pmax >= 0.80 and p_gold <= 0.20:
        return "confident_wrong"
    return "uncertain_wrong"


def mastery_label(accuracy: float, chance: float, stable_share_correct: float) -> str:
    if accuracy < chance - 0.05:
        return "低于机会水平：疑似反向规则或基本未学会"
    # Small tolerance keeps exact +5 pp cases in the chance-adjacent band.
    if accuracy <= chance + 0.051:
        return "贴近机会水平：基本未学会"
    if accuracy < 0.70:
        return "部分掌握"
    if accuracy < 0.85:
        return "基本掌握"
    if stable_share_correct >= 0.70:
        return "稳定掌握"
    return "高准确率但正确答案仍不够稳定"


def error_shape_label(error_n: int, near_miss: int, confident_wrong: int, wrong_pmax_mean: float) -> str:
    if error_n == 0:
        return "无错误"
    near_share = near_miss / error_n
    confident_share = confident_wrong / error_n
    if confident_share >= 0.35:
        return "高置信规则错主导"
    if near_share >= 0.25 and confident_share < 0.20:
        return "差一点的近失误较多"
    if wrong_pmax_mean < 0.60:
        return "候选定位或不确定性主导"
    return "混合型错误"


def summarize(name: str, name_zh: str, family: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(row["outcome_state"] for row in members)
    n = len(members)
    correct_n = sum(row["correct"] for row in members)
    error_n = n - correct_n
    chance = mean([row["chance"] for row in members])
    accuracy = correct_n / n
    stable_share_correct = ratio(states["stable_correct"], correct_n)
    fragile_share_correct = ratio(states["fragile_correct"], correct_n)
    near_share_wrong = ratio(states["near_miss_wrong"], error_n)
    confident_share_wrong = ratio(states["confident_wrong"], error_n)
    wrong_rows = [row for row in members if not row["correct"]]
    wrong_pmax_mean = mean([row["pmax"] for row in wrong_rows])
    return {
        "group_id": name,
        "name_zh": name_zh,
        "family": family,
        "n": n,
        "mean_chance": chance,
        "correct": correct_n,
        "accuracy": accuracy,
        "accuracy_minus_chance": accuracy - chance,
        "stable_correct": states["stable_correct"],
        "moderate_correct": states["moderate_correct"],
        "fragile_correct": states["fragile_correct"],
        "stable_share_of_correct": stable_share_correct,
        "fragile_share_of_correct": fragile_share_correct,
        "near_miss_wrong": states["near_miss_wrong"],
        "uncertain_wrong": states["uncertain_wrong"],
        "confident_wrong": states["confident_wrong"],
        "near_miss_share_of_wrong": near_share_wrong,
        "confident_wrong_share_of_wrong": confident_share_wrong,
        "mean_p_gold": mean([row["p_gold"] for row in members]),
        "mean_p_gold_correct": mean([row["p_gold"] for row in members if row["correct"]]),
        "mean_p_gold_wrong": mean([row["p_gold"] for row in wrong_rows]),
        "mean_margin_correct": mean([row["margin"] for row in members if row["correct"]]),
        "mean_gold_gap_wrong": mean([row["gold_gap"] for row in wrong_rows]),
        "wrong_pmax_mean": wrong_pmax_mean,
        "sl_both_correct_on_kev_wrong": sum(row["sl_both_correct"] for row in wrong_rows),
        "sl_any_correct_on_kev_wrong": sum(row["sl_any_correct"] for row in wrong_rows),
        "mastery_label": mastery_label(accuracy, chance, stable_share_correct),
        "error_shape": error_shape_label(
            error_n,
            states["near_miss_wrong"],
            states["confident_wrong"],
            wrong_pmax_mean,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--items-root", type=Path, required=True)
    parser.add_argument("--category-rules", type=Path, required=True)
    parser.add_argument("--targeted-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    prediction_rows = read_jsonl(args.predictions)
    predictions: dict[str, dict[str, dict[str, Any]]] = {}
    for row in prediction_rows:
        predictions.setdefault(row["item_id"], {})[row["model"]] = row

    items: dict[str, dict[str, Any]] = {}
    for path in sorted(args.items_root.glob("*/items.jsonl")):
        for item in read_jsonl(path):
            items[item["id"]] = item

    if len(items) != 7800 or set(items) != set(predictions):
        raise RuntimeError(
            f"coverage mismatch items={len(items)} predictions={len(predictions)} "
            f"aligned={len(set(items) & set(predictions))}"
        )

    rows: list[dict[str, Any]] = []
    for item_id in sorted(items):
        item = items[item_id]
        model_rows = predictions[item_id]
        if set(model_rows) != {"kev_blend", "startlux_instant", "startlux_autothink"}:
            raise RuntimeError(f"model coverage mismatch for {item_id}")
        pred = model_rows["kev_blend"]
        probs = {str(key): float(value) for key, value in pred["probabilities"].items()}
        gold = str(item["gold"])
        choice = str(pred["choice"])
        if gold not in probs or choice not in probs:
            raise RuntimeError(f"missing gold/choice probability for {item_id}")
        if not math.isclose(sum(probs.values()), 1.0, rel_tol=0.0, abs_tol=2e-3):
            raise RuntimeError(f"probability sum mismatch for {item_id}")
        ordered = sorted(probs.items(), key=lambda pair: (-pair[1], pair[0]))
        pmax = ordered[0][1]
        second = ordered[1][1] if len(ordered) > 1 else 0.0
        margin = pmax - second
        p_gold = probs[gold]
        gold_rank = 1 + sum(prob > p_gold + 1e-12 for _, prob in ordered)
        gold_gap = pmax - p_gold
        correct = choice == gold
        inst_correct = str(model_rows["startlux_instant"]["choice"]) == gold
        auto_correct = str(model_rows["startlux_autothink"]["choice"]) == gold
        rows.append(
            {
                "item_id": item_id,
                "task": pred["task"],
                "level": item.get("meta", {}).get("level"),
                "gold": gold,
                "choice": choice,
                "n_options": len(probs),
                "chance": 1.0 / len(probs),
                "correct": correct,
                "p_gold": p_gold,
                "pmax": pmax,
                "margin": margin,
                "gold_rank": gold_rank,
                "gold_gap": gold_gap,
                "outcome_state": classify_outcome(
                    correct, margin, gold_rank, gold_gap, pmax, p_gold
                ),
                "sl_instant_correct": inst_correct,
                "sl_autothink_correct": auto_correct,
                "sl_both_correct": inst_correct and auto_correct,
                "sl_any_correct": inst_correct or auto_correct,
            }
        )
    write_csv(args.output / "question_learning_states.csv", rows)

    by_id = {row["item_id"]: row for row in rows}
    family_profiles = [
        summarize(
            task,
            task,
            task,
            [row for row in rows if row["task"] == task],
        )
        for task in sorted({row["task"] for row in rows})
    ]
    write_csv(args.output / "family_learning_profiles.csv", family_profiles)

    level_profiles = [
        summarize(
            f"level_{level}",
            f"Level {level}",
            "all",
            [row for row in rows if row["level"] == level],
        )
        for level in (1, 2, 3)
    ]
    write_csv(args.output / "level_learning_profiles.csv", level_profiles)

    category_rules = load_category_rules(args.category_rules)
    with args.targeted_csv.open(encoding="utf-8", newline="") as handle:
        labels = {row["category_id"]: row["name_zh"] for row in csv.DictReader(handle)}
    item_by_family: dict[str, list[dict[str, Any]]] = {}
    for item in items.values():
        family = item["id"].split(":", 1)[0]
        item_by_family.setdefault(family, []).append(item)

    category_profiles: list[dict[str, Any]] = []
    membership: list[dict[str, Any]] = []
    selected_rows_by_category: dict[str, list[dict[str, Any]]] = {}
    for category_id, (family, predicate, expected_n) in category_rules.items():
        selected_items = [item for item in item_by_family[family] if predicate(item)]
        if len(selected_items) != expected_n:
            raise RuntimeError(
                f"{category_id} membership mismatch expected={expected_n} got={len(selected_items)}"
            )
        selected_rows = [by_id[item["id"]] for item in selected_items]
        selected_rows_by_category[category_id] = selected_rows
        category_profiles.append(
            summarize(category_id, labels[category_id], family, selected_rows)
        )
        membership.extend(
            {"category_id": category_id, "item_id": item["id"]}
            for item in selected_items
        )
    write_csv(args.output / "category_learning_profiles.csv", category_profiles)
    write_csv(args.output / "category_membership.csv", membership)

    category_gold_rows: list[dict[str, Any]] = []
    category_gap_rows: list[dict[str, Any]] = []
    for profile in category_profiles:
        category_id = profile["group_id"]
        selected_rows = selected_rows_by_category[category_id]
        labels_in_group = sorted({row["gold"] for row in selected_rows})
        label_summaries = []
        for gold in labels_in_group:
            gold_rows = [row for row in selected_rows if row["gold"] == gold]
            correct = sum(row["correct"] for row in gold_rows)
            summary = {
                "category_id": category_id,
                "name_zh": profile["name_zh"],
                "family": profile["family"],
                "gold": gold,
                "n": len(gold_rows),
                "correct": correct,
                "accuracy": correct / len(gold_rows),
                "stable_correct": sum(
                    row["outcome_state"] == "stable_correct" for row in gold_rows
                ),
                "fragile_correct": sum(
                    row["outcome_state"] == "fragile_correct" for row in gold_rows
                ),
                "near_miss_wrong": sum(
                    row["outcome_state"] == "near_miss_wrong" for row in gold_rows
                ),
                "confident_wrong": sum(
                    row["outcome_state"] == "confident_wrong" for row in gold_rows
                ),
                "mean_p_gold": mean([row["p_gold"] for row in gold_rows]),
            }
            category_gold_rows.append(summary)
            label_summaries.append(summary)
        if len(label_summaries) == 2 and min(row["n"] for row in label_summaries) >= 10:
            low, high = sorted(label_summaries, key=lambda row: row["accuracy"])
            category_gap_rows.append(
                {
                    "category_id": category_id,
                    "name_zh": profile["name_zh"],
                    "family": profile["family"],
                    "low_gold": low["gold"],
                    "low_n": low["n"],
                    "low_accuracy": low["accuracy"],
                    "high_gold": high["gold"],
                    "high_n": high["n"],
                    "high_accuracy": high["accuracy"],
                    "accuracy_gap": high["accuracy"] - low["accuracy"],
                }
            )
    write_csv(args.output / "category_gold_label_profiles.csv", category_gold_rows)
    category_gap_rows.sort(key=lambda row: row["accuracy_gap"], reverse=True)
    write_csv(args.output / "category_binary_label_gaps.csv", category_gap_rows)

    def pct(value: float) -> str:
        return "—" if math.isnan(value) else f"{value * 100:.1f}%"

    md = [
        "# DecisionPivot 规则掌握与概率边际全表",
        "",
        "定义：稳定正确为答对且 top1-top2 概率差至少 0.50；脆弱正确为答对但概率差小于 0.10；近失误为答错、gold 排第二且与 top1 概率差小于 0.10；高置信错误为答错、top1 概率至少 0.80 且 gold 概率不超过 0.20。脆弱正确不等于已证明为猜测。",
        "",
        "## 13 个任务族",
        "",
        "| 任务族 | 准确率 | 均匀机会水平 | 稳定正确/正确 | 脆弱正确/正确 | 近失误/错误 | 高置信错/错误 | 掌握判断 | 错误形态 |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in family_profiles:
        md.append(
            f"| `{row['group_id']}` | {pct(row['accuracy'])} | {pct(row['mean_chance'])} | "
            f"{pct(row['stable_share_of_correct'])} | {pct(row['fragile_share_of_correct'])} | "
            f"{pct(row['near_miss_share_of_wrong'])} | {pct(row['confident_wrong_share_of_wrong'])} | "
            f"{row['mastery_label']} | {row['error_shape']} |"
        )
    md.extend([
        "",
        "## 45 个重叠细分类",
        "",
        "细分类允许重叠，行数不能相加为独立题量。",
        "",
        "| 细分类 | n | 准确率 | 均匀机会水平 | 稳定正确/正确 | 脆弱正确/正确 | 近失误/错误 | 高置信错/错误 | 掌握判断 | 错误形态 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ])
    for row in category_profiles:
        md.append(
            f"| {row['name_zh']} | {row['n']} | {pct(row['accuracy'])} | {pct(row['mean_chance'])} | "
            f"{pct(row['stable_share_of_correct'])} | {pct(row['fragile_share_of_correct'])} | "
            f"{pct(row['near_miss_share_of_wrong'])} | {pct(row['confident_wrong_share_of_wrong'])} | "
            f"{row['mastery_label']} | {row['error_shape']} |"
        )
    (args.output / "learning_profiles.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    overall = summarize("overall", "全体", "all", rows)
    state_counts = Counter(row["outcome_state"] for row in rows)
    checks = {
        "items": len(rows),
        "correct": sum(row["correct"] for row in rows),
        "errors": sum(not row["correct"] for row in rows),
        "outcome_state_counts": dict(state_counts),
        "outcome_state_sum": sum(state_counts.values()),
        "family_n_sum": sum(int(row["n"]) for row in family_profiles),
        "level_n_sum": sum(int(row["n"]) for row in level_profiles),
        "category_count": len(category_profiles),
        "category_memberships_nonadditive": len(membership),
    }
    with (args.output / "learning_state_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "definitions": {
                    "stable_correct": "correct and top1-top2 margin >= 0.50",
                    "moderate_correct": "correct and 0.10 <= margin < 0.50",
                    "fragile_correct": "correct and margin < 0.10; not proof of guessing",
                    "near_miss_wrong": "wrong, gold ranked second, pmax-p_gold < 0.10",
                    "confident_wrong": "wrong, pmax >= 0.80 and p_gold <= 0.20",
                    "uncertain_wrong": "remaining wrong items",
                    "not_learned_band": "accuracy <= mean chance + 0.05",
                },
                "overall": overall,
                "checks": checks,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")


if __name__ == "__main__":
    main()
