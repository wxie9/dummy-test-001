#!/usr/bin/env python3
"""Audit whether targeted DecisionPivot gains are associated with text length."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np
from scipy.stats import pearsonr, spearmanr
from transformers import AutoTokenizer

from scripts.analyze_decisionpivot_targeted_categories import CATEGORY_RULES


SPECIAL_OVERHEAD = {
    "state": 1,
    "question": 1,
    "option": 2,
    "decide": 1,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def render(value: Any, indent: int = 0) -> str:
    """Match Kev's recursive JSONContent renderer."""
    pad = "  " * indent
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(f"{pad}- {render(item, indent + 1).lstrip()}" for item in value)
    return "\n".join(
        f"{pad}{key}:\n{render(item, indent + 1)}"
        if isinstance(item, (dict, list))
        else f"{pad}{key}: {render(item)}"
        for key, item in value.items()
    )


def option_text(name: str, description: Any) -> str:
    return name if description is None or description == "" else f"{name}: {render(description)}"


def question_parts(question: dict[str, Any]) -> tuple[str, list[str]]:
    instruction = render(question["instructions"])
    qtype = question["type"]
    criteria = question.get("criteria")
    if qtype == "noul":
        criteria = criteria or {}
        options = [option_text("no", criteria.get("false")), option_text("yes", criteria.get("true"))]
    elif qtype == "choice":
        options = [option_text(key, value) for key, value in criteria.items()]
    else:
        options = [render(value) for value in criteria]
    return instruction, options


def lengths(row: dict[str, Any], tokenizer: Any) -> dict[str, int]:
    state_text = render(row["state"])
    state_tokens = len(tokenizer.encode(state_text, add_special_tokens=False))
    packed_tokens = SPECIAL_OVERHEAD["state"] + state_tokens
    full_text_parts = [state_text]
    for question in row["questions"].values():
        instruction, options = question_parts(question)
        packed_tokens += SPECIAL_OVERHEAD["question"]
        packed_tokens += len(tokenizer.encode(instruction, add_special_tokens=False))
        full_text_parts.append(instruction)
        for option in options:
            packed_tokens += SPECIAL_OVERHEAD["option"]
            packed_tokens += len(tokenizer.encode(option, add_special_tokens=False))
            full_text_parts.append(option)
        packed_tokens += SPECIAL_OVERHEAD["decide"]
    return {
        "state_chars": len(state_text),
        "state_tokens": state_tokens + SPECIAL_OVERHEAD["state"],
        "full_chars": sum(len(part) for part in full_text_parts),
        "packed_tokens": packed_tokens,
    }


def describe(values: list[float]) -> dict[str, float]:
    ordered = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(ordered)),
        "median": float(np.median(ordered)),
        "p10": float(np.percentile(ordered, 10)),
        "p90": float(np.percentile(ordered, 90)),
        "min": float(np.min(ordered)),
        "max": float(np.max(ordered)),
    }


def correlation(x: list[float], y: list[float]) -> dict[str, float]:
    pearson = pearsonr(x, y)
    spearman = spearmanr(x, y)
    return {
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rendered", type=Path, required=True)
    parser.add_argument("--eval-data-root", type=Path, required=True)
    parser.add_argument("--category-results", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, trust_remote_code=True)
    category_results = {
        row["category_id"]: row
        for row in json.loads(args.category_results.read_text(encoding="utf-8"))["categories"]
        if row["generated_n"] > 0
    }

    train_by_category: dict[str, list[dict[str, int]]] = defaultdict(list)
    for row in read_jsonl(args.rendered):
        category_id = row["_meta"]["pivot_category_id"]
        train_by_category[category_id].append(lengths(row, tokenizer))

    eval_by_category: dict[str, list[dict[str, int]]] = defaultdict(list)
    for category_id, (family, predicate, expected_n) in CATEGORY_RULES.items():
        if category_id not in category_results:
            continue
        items = read_jsonl(args.eval_data_root / "tasks" / family / "items.jsonl")
        members = [item for item in items if predicate(item)]
        if len(members) != expected_n:
            raise RuntimeError(f"{category_id}: expected {expected_n} eval rows, got {len(members)}")
        eval_by_category[category_id] = [lengths(item, tokenizer) for item in members]

    rows: list[dict[str, Any]] = []
    for category_id, result in category_results.items():
        train = train_by_category[category_id]
        evaluation = eval_by_category[category_id]
        row: dict[str, Any] = {
            "rank": result["rank"],
            "category_id": category_id,
            "name_zh": result["name_zh"],
            "family": CATEGORY_RULES[category_id][0],
            "generated_n": result["generated_n"],
            "eval_n": result["eval_n"],
            "full_minus_v1_pp": result["full_minus_v1"] * 100,
            "blend_minus_v1_pp": result["blend_minus_v1"] * 100,
            "blend_direction": result["blend_direction"],
        }
        for metric in ("state_chars", "state_tokens", "full_chars", "packed_tokens"):
            train_summary = describe([item[metric] for item in train])
            eval_summary = describe([item[metric] for item in evaluation])
            for stat, value in train_summary.items():
                row[f"train_{metric}_{stat}"] = value
            for stat, value in eval_summary.items():
                row[f"eval_{metric}_{stat}"] = value
            row[f"{metric}_mean_ratio_train_eval"] = train_summary["mean"] / eval_summary["mean"]
            row[f"{metric}_mean_log_mismatch"] = abs(math.log(train_summary["mean"] / eval_summary["mean"]))
        rows.append(row)
    rows.sort(key=lambda row: row["rank"])

    y_full = [row["full_minus_v1_pp"] for row in rows]
    y_blend = [row["blend_minus_v1_pp"] for row in rows]
    features = {
        "train_state_tokens_mean": [row["train_state_tokens_mean"] for row in rows],
        "train_packed_tokens_mean": [row["train_packed_tokens_mean"] for row in rows],
        "eval_state_tokens_mean": [row["eval_state_tokens_mean"] for row in rows],
        "state_token_log_mismatch": [row["state_tokens_mean_log_mismatch"] for row in rows],
        "packed_token_log_mismatch": [row["packed_tokens_mean_log_mismatch"] for row in rows],
    }
    correlations = {
        feature: {
            "vs_full_minus_v1": correlation(values, y_full),
            "vs_blend_minus_v1": correlation(values, y_blend),
        }
        for feature, values in features.items()
    }

    # Remove task-family means to test whether length explains differences among
    # nearby slices rather than merely identifying inherently longer families.
    def residualize(values: list[float]) -> list[float]:
        by_family: dict[str, list[float]] = defaultdict(list)
        for row, value in zip(rows, values):
            by_family[row["family"]].append(value)
        family_means = {family: mean(group) for family, group in by_family.items()}
        return [value - family_means[row["family"]] for row, value in zip(rows, values)]

    within_family = {
        "train_state_tokens_mean": correlation(
            residualize(features["train_state_tokens_mean"]), residualize(y_blend)
        ),
        "train_packed_tokens_mean": correlation(
            residualize(features["train_packed_tokens_mean"]), residualize(y_blend)
        ),
        "state_token_log_mismatch": correlation(
            residualize(features["state_token_log_mismatch"]), residualize(y_blend)
        ),
    }

    direction_summary: dict[str, Any] = {}
    for direction in ("up", "flat", "down"):
        subset = [row for row in rows if row["blend_direction"] == direction]
        direction_summary[direction] = {
            "categories": len(subset),
            "train_state_tokens_mean_of_category_means": mean(row["train_state_tokens_mean"] for row in subset),
            "train_state_tokens_median_of_category_means": median(row["train_state_tokens_mean"] for row in subset),
            "train_packed_tokens_mean_of_category_means": mean(row["train_packed_tokens_mean"] for row in subset),
            "state_token_ratio_train_eval_mean": mean(row["state_tokens_mean_ratio_train_eval"] for row in subset),
        }

    output = {
        "meta": {
            "categories": len(rows),
            "records": sum(len(values) for values in train_by_category.values()),
            "tokenizer_class": type(tokenizer).__name__,
            "tokenizer_size": len(tokenizer),
            "length_definition": "Kev render(state), plus question instruction/options and exact delimiter overhead for packed_tokens",
        },
        "correlations": correlations,
        "within_family_residual_correlations_vs_blend": within_family,
        "direction_summary": direction_summary,
        "categories": rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "length_effect.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        "# DecisionPivot 定向数据长度—效果审计",
        "",
        f"43个实际生成细类、{output['meta']['records']:,}条训练记录；tokenizer={output['meta']['tokenizer_class']}。",
        "",
        "## 相关性",
        "",
        "| 长度特征 | Pearson r（融合增益） | p | Spearman ρ | p |",
        "|---|---:|---:|---:|---:|",
    ]
    for feature, values in correlations.items():
        result = values["vs_blend_minus_v1"]
        md.append(
            f"| {feature} | {result['pearson_r']:.3f} | {result['pearson_p']:.3g} | "
            f"{result['spearman_rho']:.3f} | {result['spearman_p']:.3g} |"
        )
    md.extend([
        "",
        "## 按最终方向分组",
        "",
        "| 最终方向 | 类别数 | 平均state tokens | 类别均值的中位state tokens | 平均packed tokens | 平均训练/评测state长度比 |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for direction, values in direction_summary.items():
        md.append(
            f"| {direction} | {values['categories']} | "
            f"{values['train_state_tokens_mean_of_category_means']:.1f} | "
            f"{values['train_state_tokens_median_of_category_means']:.1f} | "
            f"{values['train_packed_tokens_mean_of_category_means']:.1f} | "
            f"{values['state_token_ratio_train_eval_mean']:.3f} |"
        )
    md.extend([
        "",
        "## 各细类",
        "",
        "| 排名 | 细类 | 生成量 | 训练state tokens | 测试state tokens | 训练/测试比 | 融合−v1 (pp) |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        md.append(
            f"| {row['rank']} | {row['name_zh']} | {row['generated_n']} | "
            f"{row['train_state_tokens_mean']:.1f} | {row['eval_state_tokens_mean']:.1f} | "
            f"{row['state_tokens_mean_ratio_train_eval']:.3f} | {row['blend_minus_v1_pp']:+.2f} |"
        )
    (args.output_dir / "length_effect.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"correlations": correlations, "within_family": within_family, "direction_summary": direction_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
