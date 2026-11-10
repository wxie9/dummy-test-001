#!/usr/bin/env python3
"""Export aligned DecisionPivot option probabilities from three run folders."""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import os
from pathlib import Path


MODELS = (
    ("kev_blend", "kev_blend"),
    ("startlux_instant", "startlux_instant"),
    ("startlux_autothink", "startlux_autothink"),
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_confidence(probabilities: dict[str, float]) -> float:
    n = len(probabilities)
    if n < 2:
        return 1.0
    pmax = max(probabilities.values())
    return min(1.0, max(0.0, (n * pmax - 1.0) / (n - 1.0)))


def load_run(model: str, run_dir: Path) -> list[dict]:
    records = []
    for path_text in sorted(glob.glob(str(run_dir / "*.jsonl"))):
        path = Path(path_text)
        task = path.stem
        with path.open(encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                row = json.loads(line)
                if row.get("error"):
                    raise ValueError(f"{path}:{line_no}: error row: {row['error']}")
                answers = row.get("answers") or {}
                for question_id, answer in answers.items():
                    probabilities = answer.get("probabilities")
                    if not isinstance(probabilities, dict) or not probabilities:
                        raise ValueError(f"{path}:{line_no}: missing probabilities")
                    probabilities = {str(k): float(v) for k, v in probabilities.items()}
                    record = {
                        "model": model,
                        "task": task,
                        "item_id": str(row["id"]),
                        "question_id": str(question_id),
                        "choice": answer.get("choice"),
                        "confidence": float(answer["confidence"]),
                        "none_probability": (
                            float(answer["none_probability"])
                            if answer.get("none_probability") is not None
                            else None
                        ),
                        "probabilities": probabilities,
                    }
                    record["key"] = f"{task}\t{record['item_id']}\t{record['question_id']}"
                    records.append(record)
    records.sort(key=lambda x: (x["task"], x["item_id"], x["question_id"]))
    return records


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            out = {k: v for k, v in row.items() if k != "key"}
            f.write(json.dumps(out, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kev-blend", type=Path, required=True)
    ap.add_argument("--startlux-instant", type=Path, required=True)
    ap.add_argument("--startlux-autothink", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sources = {
        "kev_blend": args.kev_blend,
        "startlux_instant": args.startlux_instant,
        "startlux_autothink": args.startlux_autothink,
    }
    by_model = {model: load_run(model, path) for model, path in sources.items()}

    key_sets = {model: {row["key"] for row in rows} for model, rows in by_model.items()}
    reference = key_sets["kev_blend"]
    if any(keys != reference for keys in key_sets.values()):
        detail = {model: len(keys) for model, keys in key_sets.items()}
        raise ValueError(f"run key sets do not match: {detail}")

    all_rows = []
    validations = {}
    output_files = []
    for model, _ in MODELS:
        rows = by_model[model]
        question_path = args.out / f"{model}_questions.jsonl"
        write_jsonl(question_path, rows)
        output_files.append(question_path)
        all_rows.extend(rows)

        prob_sum_errors = []
        conf_errors = []
        choice_errors = 0
        none_count = 0
        option_rows = 0
        for row in rows:
            p = row["probabilities"]
            prob_sum_errors.append(abs(sum(p.values()) - 1.0))
            conf_errors.append(abs(row["confidence"] - expected_confidence(p)))
            if row["choice"] != max(p, key=p.get):
                choice_errors += 1
            if row["none_probability"] is not None:
                none_count += 1
            option_rows += len(p)
        validations[model] = {
            "questions": len(rows),
            "option_rows": option_rows,
            "none_probability_present": none_count,
            "max_probability_sum_error": max(prob_sum_errors, default=0.0),
            "choice_not_argmax": choice_errors,
            "max_confidence_formula_error": max(conf_errors, default=0.0),
        }

    all_rows.sort(key=lambda x: (x["task"], x["item_id"], x["question_id"], x["model"]))
    combined_jsonl = args.out / "all_three_questions.jsonl"
    write_jsonl(combined_jsonl, all_rows)
    output_files.append(combined_jsonl)

    question_csv = args.out / "all_three_question_level.csv"
    with question_csv.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "model", "task", "item_id", "question_id", "choice", "confidence",
            "none_probability", "probabilities_json",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in all_rows:
            w.writerow({
                "model": row["model"],
                "task": row["task"],
                "item_id": row["item_id"],
                "question_id": row["question_id"],
                "choice": row["choice"],
                "confidence": format(row["confidence"], ".17g"),
                "none_probability": (
                    "" if row["none_probability"] is None
                    else format(row["none_probability"], ".17g")
                ),
                "probabilities_json": json.dumps(
                    row["probabilities"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            })
    output_files.append(question_csv)

    option_csv = args.out / "all_three_option_level.csv"
    with option_csv.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "model", "task", "item_id", "question_id", "choice", "confidence",
            "none_probability", "option_id", "option_probability", "is_selected",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in all_rows:
            for option_id, probability in row["probabilities"].items():
                w.writerow({
                    "model": row["model"],
                    "task": row["task"],
                    "item_id": row["item_id"],
                    "question_id": row["question_id"],
                    "choice": row["choice"],
                    "confidence": format(row["confidence"], ".17g"),
                    "none_probability": (
                        "" if row["none_probability"] is None
                        else format(row["none_probability"], ".17g")
                    ),
                    "option_id": option_id,
                    "option_probability": format(probability, ".17g"),
                    "is_selected": int(option_id == row["choice"]),
                })
    output_files.append(option_csv)

    source_files = {
        model: {
            str(path.relative_to(sources[model])): sha256(path)
            for path in sorted(sources[model].glob("*.jsonl"))
        }
        for model in sources
    }
    manifest = {
        "schema": "decisionpivot-probability-export-v1",
        "models": [model for model, _ in MODELS],
        "aligned_question_keys": len(reference),
        "validations": validations,
        "source_directories": {model: str(path) for model, path in sources.items()},
        "source_jsonl_sha256": source_files,
        "output_sha256": {path.name: sha256(path) for path in output_files},
        "notes": [
            "Kev probabilities/confidence are stored to about four decimal places in the source run.",
            "StartLux probabilities/confidence retain full JSON floating-point precision.",
            "StartLux none_probability is separate from probabilities, which are renormalised over listed options.",
            "Kev DecisionPivot outputs do not contain none_probability; the export stores null/blank.",
            "confidence is the TypeSafe choice confidence transform of the maximum listed-option probability.",
        ],
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    readme = args.out / "README.md"
    readme.write_text(
        "# DecisionPivot 三模型逐题概率导出\n\n"
        "本目录对齐了 Kev 融合版、StartLux Instant 和 StartLux AutoThink 的 7,800 道"
        " DecisionPivot Core 1.1 题目。没有重新推理；全部字段来自已有运行归档。\n\n"
        "## 文件\n\n"
        "- `kev_blend_questions.jsonl`：Kev 融合版逐题结果。\n"
        "- `startlux_instant_questions.jsonl`：StartLux Instant 逐题结果。\n"
        "- `startlux_autothink_questions.jsonl`：StartLux AutoThink 逐题结果。\n"
        "- `all_three_questions.jsonl`：三模型合并的逐题 JSONL。\n"
        "- `all_three_question_level.csv`：每个模型每题一行，概率字典放在 `probabilities_json`。\n"
        "- `all_three_option_level.csv`：每个选项一行，便于透视、筛选和画图。\n"
        "- `manifest.json`：来源哈希、输出哈希、计数及一致性检查。\n\n"
        "## 字段边界\n\n"
        "Kev 源文件的概率约保留四位小数，StartLux 保留完整 JSON 浮点精度。"
        "Kev 没有 `none_probability`，因此在 JSONL 中为 `null`、CSV 中为空。"
        "StartLux 的 `none_probability` 是候选集合之外的额外概率；`probabilities` 已在正常候选内部归一化。\n",
        encoding="utf-8",
    )
    print(json.dumps({"out": str(args.out), "manifest": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
