"""Score a selected Decision Index rows file without pretending it is the full DI suite."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from decision_index.scoring.report import load_results, score
from decision_index.suite.io import read_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = list(read_jsonl(args.rows))
    results = load_results(args.results)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["_evaluation"]["catalog_id"]].append(row)
    summary = {
        "scope": "Selected traditional DI benchmarks only; no full-suite Decision Index is calculated.",
        "rows": str(Path(args.rows).resolve()),
        "results": str(Path(args.results).resolve()),
        "benchmarks": {str(catalog_id): score(entries, results) for catalog_id, entries in sorted(grouped.items())},
    }
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
