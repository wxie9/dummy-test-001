#!/usr/bin/env python3
"""Build a reviewed, portable snapshot for the DecisionPivot probability-error report."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / (
    "artifacts/kev_training_eval_20261026/"
    "decisionpivot_probability_exports_20261110/large_error_analysis"
)
OUTPUT = ANALYSIS / "report_app_snapshot.json"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: str) -> int:
    return int(value)


def as_float(value: str) -> float:
    return float(value)


summary = json.loads((ANALYSIS / "summary.json").read_text(encoding="utf-8"))
family = read_csv("family_large_error_profile.csv")
levels = read_csv("level_large_error_profile.csv")
directions = read_csv("binary_direction_large_errors.csv")

query_list = [
    {
        "id": "overall",
        "label": "总体统计",
        "columns": ["metric", "value", "note"],
        "rows": [
            {"metric": "评测题数", "value": 7800, "note": "DecisionPivot Core 1.1"},
            {"metric": "答对", "value": 5547, "note": "71.12%"},
            {"metric": "答错", "value": 2253, "note": "28.88%"},
            {"metric": "大错", "value": 1709, "note": "占错题75.85%；占全部21.91%"},
            {"metric": "小错", "value": 544, "note": "gold第2且概率差不超过0.30"},
        ],
        "totals": {"all": 7800, "correct": 5547, "wrong": 2253, "large": 1709},
    },
    {
        "id": "threshold-sensitivity",
        "label": "大错阈值敏感性",
        "columns": ["threshold", "large_errors", "share_wrong", "share_all"],
        "rows": [
            {"threshold": 0.10, "large_errors": 2057, "share_wrong": 0.9130, "share_all": 0.2637},
            {"threshold": 0.20, "large_errors": 1859, "share_wrong": 0.8251, "share_all": 0.2383},
            {"threshold": 0.30, "large_errors": 1709, "share_wrong": 0.7585, "share_all": 0.2191},
            {"threshold": 0.40, "large_errors": 1550, "share_wrong": 0.6880, "share_all": 0.1987},
            {"threshold": 0.50, "large_errors": 1377, "share_wrong": 0.6112, "share_all": 0.1765},
        ],
    },
    {
        "id": "family-large-errors",
        "label": "任务族大错",
        "columns": ["task", "n", "errors", "large_errors", "large_error_rate_all", "gold_rank_3plus"],
        "rows": [
            {
                "task": row["task"],
                "n": as_int(row["n"]),
                "errors": as_int(row["errors"]),
                "large_errors": as_int(row["large_errors"]),
                "large_error_rate_all": as_float(row["large_error_rate_all"]),
                "gold_rank_3plus": as_int(row["gold_rank_3plus"]),
            }
            for row in family
        ],
        "totals": {"large_errors": sum(as_int(row["large_errors"]) for row in family)},
    },
    {
        "id": "level-large-errors",
        "label": "难度层大错",
        "columns": ["level", "n", "errors", "large_errors", "large_error_rate_all", "share_of_all_large_errors"],
        "rows": [
            {
                "level": as_int(row["level"]),
                "n": as_int(row["n"]),
                "errors": as_int(row["errors"]),
                "large_errors": as_int(row["large_errors"]),
                "large_error_rate_all": as_float(row["large_error_rate_all"]),
                "share_of_all_large_errors": as_float(row["share_of_all_large_errors"]),
            }
            for row in levels
        ],
        "totals": {"large_errors": sum(as_int(row["large_errors"]) for row in levels)},
    },
    {
        "id": "direction-large-errors",
        "label": "二元任务方向偏置",
        "columns": ["task", "gold", "n", "errors", "large_errors", "large_error_rate_all"],
        "rows": [
            {
                "task": row["task"],
                "gold": row["gold"],
                "n": as_int(row["n"]),
                "errors": as_int(row["errors"]),
                "large_errors": as_int(row["large_errors"]),
                "large_error_rate_all": as_float(row["large_error_rate_all"]),
            }
            for row in directions
        ],
    },
]

snapshot = {
    "schemaVersion": 1,
    "surface": "report",
    "title": "Kev融合版 DecisionPivot 概率错题与错因统计分析",
    "subtitle": "从逐题概率到1,709道大错，再到可复核的行为机制",
    "generatedAt": "2026-11-10T00:00:00+08:00",
    "buildStatus": "creating",
    "source": {
        "type": "local-reviewed-artifacts",
        "files": [
            "summary.json",
            "family_large_error_profile.csv",
            "level_large_error_profile.csv",
            "binary_direction_large_errors.csv",
            "large_error_questions.jsonl",
        ],
        "note": "全部结果来自既有7,800题评测归档，本报告未重新运行模型。",
    },
    "definition": summary["definition"],
    "metricDefinitions": {
        "gold_gap": "pmax - p_gold",
        "large_error": "仅对错题：gold_rank != 2，或gold_rank == 2且gold_gap > 0.30",
        "large_error_rate_all": "子组大错题数 / 子组全部题数",
    },
    "evidenceFlow": [
        "按item_id + question_id对齐Kev、StartLux Instant、StartLux AutoThink与原题",
        "校验选项概率、choice=argmax和7,800题完整覆盖",
        "计算pmax、p_gold、gold_rank、top1-top2 margin与gold gap",
        "先做六状态概率边际审计，再按0.30规则重分大错与小错",
        "用任务族、Level、答案方向和StartLux交叉检查定位行为机制",
        "把观察、机制解释和训练侧根因分成不同证据等级",
    ],
    "caveats": [
        "没有保存Kev原始CoT，不能把事后解释当成真实思维链。",
        "0.30是本轮诊断阈值，不是DecisionPivot官方指标。",
        "45细类和元数据切片相互重叠，不得相加。",
        "除日志off_by_one生成器错配外，其他错因是行为机制而非已证实的训练因果。",
    ],
    "queries": {query["id"]: query for query in query_list},
}

OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUTPUT)
