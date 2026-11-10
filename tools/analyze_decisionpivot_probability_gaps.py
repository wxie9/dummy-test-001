#!/usr/bin/env python3
"""Compare aligned DecisionPivot option distributions across three systems."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


PAIRS = (
    ("kev_blend", "startlux_instant"),
    ("kev_blend", "startlux_autothink"),
    ("startlux_instant", "startlux_autothink"),
)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def load_predictions(path: Path) -> dict[tuple[str, str, str, str], dict]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            key = (row["model"], row["task"], row["item_id"], row["question_id"])
            out[key] = row
    return out


def load_items(root: Path) -> dict[tuple[str, str, str], dict]:
    out = {}
    for task_dir in sorted(root.iterdir()):
        path = task_dir / "items.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                for question_id in row["questions"]:
                    out[(task_dir.name, str(row["id"]), str(question_id))] = row
    return out


def preview(item: dict, limit: int = 500) -> str:
    state = item.get("state")
    if isinstance(state, dict):
        text = state.get("question") or state.get("query") or json.dumps(state, ensure_ascii=False)
    else:
        text = str(state)
    text = " ".join(text.split())
    return text[:limit]


def outcome(a_correct: bool, b_correct: bool, a_choice: str, b_choice: str) -> str:
    if a_correct and b_correct:
        return "both_correct"
    if a_correct:
        return "a_only_correct"
    if b_correct:
        return "b_only_correct"
    return "both_wrong_same" if a_choice == b_choice else "both_wrong_different"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", type=Path, required=True)
    ap.add_argument("--items-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--top", type=int, default=100)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    predictions = load_predictions(args.predictions)
    items = load_items(args.items_root)
    model_rows = defaultdict(dict)
    for (model, task, item_id, qid), row in predictions.items():
        model_rows[model][(task, item_id, qid)] = row

    common = set(items)
    for model in model_rows:
        common &= set(model_rows[model])
    if len(common) != 7800:
        raise ValueError(f"expected 7800 aligned keys, got {len(common)}")

    pair_rows = []
    detailed_rows = []
    for model_a, model_b in PAIRS:
        pair_name = f"{model_a}__vs__{model_b}"
        for key in sorted(common):
            task, item_id, qid = key
            a = model_rows[model_a][key]
            b = model_rows[model_b][key]
            item = items[key]
            pa = a["probabilities"]
            pb = b["probabilities"]
            options = sorted(set(pa) | set(pb))
            abs_gaps = {o: abs(float(pa.get(o, 0.0)) - float(pb.get(o, 0.0))) for o in options}
            signed_gaps = {o: float(pb.get(o, 0.0)) - float(pa.get(o, 0.0)) for o in options}
            tv = 0.5 * sum(abs_gaps.values())
            gold = str(item["gold"])
            a_correct = str(a["choice"]) == gold
            b_correct = str(b["choice"]) == gold
            row = {
                "pair": pair_name,
                "model_a": model_a,
                "model_b": model_b,
                "task": task,
                "item_id": item_id,
                "question_id": qid,
                "group": item.get("group"),
                "gold": gold,
                "choice_a": a["choice"],
                "choice_b": b["choice"],
                "correct_a": int(a_correct),
                "correct_b": int(b_correct),
                "outcome": outcome(a_correct, b_correct, str(a["choice"]), str(b["choice"])),
                "choice_disagree": int(a["choice"] != b["choice"]),
                "confidence_a": float(a["confidence"]),
                "confidence_b": float(b["confidence"]),
                "confidence_gap_b_minus_a": float(b["confidence"]) - float(a["confidence"]),
                "abs_confidence_gap": abs(float(b["confidence"]) - float(a["confidence"])),
                "none_probability_a": a.get("none_probability"),
                "none_probability_b": b.get("none_probability"),
                "tv_distance": tv,
                "max_abs_option_gap": max(abs_gaps.values()),
                "max_gap_option": max(abs_gaps, key=abs_gaps.get),
                "probabilities_a": pa,
                "probabilities_b": pb,
                "signed_probability_gap_b_minus_a": signed_gaps,
                "question_preview": preview(item),
                "meta": item.get("meta"),
            }
            pair_rows.append(row)
            detailed_rows.append({**row, "state": item.get("state"), "questions": item.get("questions")})

    pair_rows.sort(key=lambda r: (r["pair"], -r["tv_distance"], r["task"], r["item_id"]))
    detailed_rows.sort(key=lambda r: (r["pair"], -r["tv_distance"], r["task"], r["item_id"]))

    columns = [
        "pair", "model_a", "model_b", "task", "item_id", "question_id", "group", "gold",
        "choice_a", "choice_b", "correct_a", "correct_b", "outcome", "choice_disagree",
        "confidence_a", "confidence_b", "confidence_gap_b_minus_a", "abs_confidence_gap",
        "none_probability_a", "none_probability_b", "tv_distance", "max_abs_option_gap",
        "max_gap_option", "probabilities_a_json", "probabilities_b_json",
        "signed_probability_gap_b_minus_a_json", "question_preview", "meta_json",
    ]
    all_path = args.out / "all_pairwise_question_gaps.csv"
    with all_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in pair_rows:
            w.writerow({
                **{k: r.get(k) for k in columns if not k.endswith("_json")},
                "probabilities_a_json": json.dumps(r["probabilities_a"], ensure_ascii=False, sort_keys=True),
                "probabilities_b_json": json.dumps(r["probabilities_b"], ensure_ascii=False, sort_keys=True),
                "signed_probability_gap_b_minus_a_json": json.dumps(
                    r["signed_probability_gap_b_minus_a"], ensure_ascii=False, sort_keys=True
                ),
                "meta_json": json.dumps(r["meta"], ensure_ascii=False, sort_keys=True),
            })

    top_rows = []
    for model_a, model_b in PAIRS:
        pair_name = f"{model_a}__vs__{model_b}"
        selected = [r for r in pair_rows if r["pair"] == pair_name][: args.top]
        top_rows.extend(selected)
    top_path = args.out / f"top{args.top}_per_pair.csv"
    with top_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in top_rows:
            w.writerow({
                **{k: r.get(k) for k in columns if not k.endswith("_json")},
                "probabilities_a_json": json.dumps(r["probabilities_a"], ensure_ascii=False, sort_keys=True),
                "probabilities_b_json": json.dumps(r["probabilities_b"], ensure_ascii=False, sort_keys=True),
                "signed_probability_gap_b_minus_a_json": json.dumps(
                    r["signed_probability_gap_b_minus_a"], ensure_ascii=False, sort_keys=True
                ),
                "meta_json": json.dumps(r["meta"], ensure_ascii=False, sort_keys=True),
            })

    top_keys = {(r["pair"], r["task"], r["item_id"], r["question_id"]) for r in top_rows}
    detail_path = args.out / f"top{args.top}_per_pair_detailed.jsonl"
    with detail_path.open("w", encoding="utf-8") as f:
        for r in detailed_rows:
            key = (r["pair"], r["task"], r["item_id"], r["question_id"])
            if key in top_keys:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    summary_rows = []
    for model_a, model_b in PAIRS:
        pair_name = f"{model_a}__vs__{model_b}"
        for task in ["ALL"] + sorted({r["task"] for r in pair_rows if r["pair"] == pair_name}):
            rs = [r for r in pair_rows if r["pair"] == pair_name and (task == "ALL" or r["task"] == task)]
            tvs = [r["tv_distance"] for r in rs]
            outcomes = Counter(r["outcome"] for r in rs)
            summary_rows.append({
                "pair": pair_name,
                "task": task,
                "n": len(rs),
                "mean_tv": statistics.fmean(tvs),
                "median_tv": statistics.median(tvs),
                "p90_tv": percentile(tvs, 0.90),
                "p95_tv": percentile(tvs, 0.95),
                "max_tv": max(tvs),
                "n_tv_ge_0_25": sum(v >= 0.25 for v in tvs),
                "n_tv_ge_0_50": sum(v >= 0.50 for v in tvs),
                "n_tv_ge_0_75": sum(v >= 0.75 for v in tvs),
                "choice_disagree": sum(r["choice_disagree"] for r in rs),
                "accuracy_a": sum(r["correct_a"] for r in rs) / len(rs),
                "accuracy_b": sum(r["correct_b"] for r in rs) / len(rs),
                "a_only_correct": outcomes["a_only_correct"],
                "b_only_correct": outcomes["b_only_correct"],
                "both_correct": outcomes["both_correct"],
                "both_wrong_same": outcomes["both_wrong_same"],
                "both_wrong_different": outcomes["both_wrong_different"],
            })
    summary_path = args.out / "task_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0]))
        w.writeheader()
        w.writerows(summary_rows)

    top_task_rows = []
    for model_a, model_b in PAIRS:
        pair_name = f"{model_a}__vs__{model_b}"
        selected = [r for r in pair_rows if r["pair"] == pair_name][: args.top]
        counts = Counter(r["task"] for r in selected)
        for task, count in counts.most_common():
            top_task_rows.append({"pair": pair_name, "top_n": args.top, "task": task, "count": count})
    top_task_path = args.out / f"top{args.top}_task_counts.csv"
    with top_task_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pair", "top_n", "task", "count"])
        w.writeheader()
        w.writerows(top_task_rows)

    headline = {r["pair"]: r for r in summary_rows if r["task"] == "ALL"}
    json_path = args.out / "summary.json"
    json_path.write_text(json.dumps({
        "metric": {
            "name": "total_variation_distance",
            "formula": "0.5 * sum_i abs(p_i - q_i)",
            "range": [0, 1],
            "scope": "listed-option probabilities only; StartLux none_probability excluded for fair Kev comparison",
        },
        "aligned_questions": len(common),
        "top_n_per_pair": args.top,
        "headline": headline,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"out": str(args.out), "headline": headline}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
