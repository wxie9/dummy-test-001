#!/usr/bin/env python3
"""Summarize the six standard Kev evaluation reports with coverage checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUITES = (
    "decision-v7",
    "transfer-v4",
    "transfer-v9",
    "hard-v1",
    "devtools-v1",
    "documents-v1",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    suites: dict[str, dict] = {}
    correct_total = 0.0
    n_total = 0
    requested_total = 0
    evaluated_total = 0
    rejected_total = 0
    truncated_total = 0

    for name in SUITES:
        report_path = args.root / name / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        clean = report["clean"]
        coverage = report["coverage"]
        n = int(clean["n"])
        correct = float(clean["acc"]) * n
        suites[name] = {
            "n": n,
            "correct": round(correct),
            "accuracy": float(clean["acc"]),
            "requested_records": int(coverage["requested_records"]),
            "requested_questions": int(coverage["requested_questions"]),
            "evaluated_records": int(coverage["evaluated_records"]),
            "evaluated_questions": int(coverage["evaluated_questions"]),
            "rejected_records": int(coverage["rejected_records"]),
            "truncated_records": int(coverage["truncated_records"]),
        }
        correct_total += correct
        n_total += n
        requested_total += int(coverage["requested_questions"])
        evaluated_total += int(coverage["evaluated_questions"])
        rejected_total += int(coverage["rejected_records"])
        truncated_total += int(coverage["truncated_records"])

    summary = {
        "root": str(args.root),
        "suites": suites,
        "weighted": {
            "n": n_total,
            "correct": round(correct_total),
            "accuracy": correct_total / n_total,
            "requested_questions": requested_total,
            "evaluated_questions": evaluated_total,
            "rejected_records": rejected_total,
            "truncated_records": truncated_total,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
