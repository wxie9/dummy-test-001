#!/usr/bin/env python3
"""Generate solver-labelled structured scaffolds for the Pivot 20K tranche."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import atomic_write_jsonl, read_jsonl  # noqa: E402
from pivot_generators import generate_structured, validate_structured  # noqa: E402
from pivot_spec import CATEGORIES, CATEGORY_BY_ID, total_target  # noqa: E402


def _existing(path: Path) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    state_hashes = set()
    for row in read_jsonl(path):
        problems = validate_structured(row)
        if problems:
            raise ValueError(f"invalid existing row {row.get('id')}: {'; '.join(problems)}")
        if row["id"] in rows or row["_meta"]["state_sha256"] in state_hashes:
            raise ValueError(f"duplicate existing id/state: {row['id']}")
        rows[row["id"]] = row
        state_hashes.add(row["_meta"]["state_sha256"])
    return rows


def generate_rows(category_ids: Iterable[str], seed: int, limit_per_category: int | None, existing: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = dict(existing)
    hashes = {row["_meta"]["state_sha256"] for row in rows.values()}
    for category_id in category_ids:
        target = CATEGORY_BY_ID[category_id].target
        if limit_per_category is not None:
            target = min(target, limit_per_category)
        for index in range(target):
            record_id = f"kev-pivot-augmentation-v1/{category_id}/{index:06d}"
            if record_id in rows:
                continue
            row = generate_structured(category_id, index, seed)
            state_hash = row["_meta"]["state_sha256"]
            if state_hash in hashes:
                raise ValueError(f"duplicate semantic state across generated rows: {record_id}")
            rows[record_id] = row
            hashes.add(state_hash)
    return [rows[key] for key in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs/kev-v2-pivot-augmentation/structured.jsonl"))
    parser.add_argument("--seed", type=int, default=20261106)
    parser.add_argument("--category", choices=sorted(CATEGORY_BY_ID))
    parser.add_argument("--limit-per-category", type=int, help="smoke-test cap; categories with target 0 remain empty")
    parser.add_argument("--fresh", action="store_true", help="ignore an existing output instead of resuming it")
    args = parser.parse_args()
    if args.limit_per_category is not None and args.limit_per_category < 1:
        parser.error("--limit-per-category must be positive")

    started = time.time()
    existing = {} if args.fresh else _existing(args.out)
    category_ids = [args.category] if args.category else [spec.category_id for spec in CATEGORIES]
    rows = generate_rows(category_ids, args.seed, args.limit_per_category, existing)
    atomic_write_jsonl(args.out, rows)
    payload = args.out.read_bytes()
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row["category_id"]] = counts.get(row["category_id"], 0) + 1
    manifest = {
        "records": len(rows),
        "full_target": total_target(),
        "complete": args.limit_per_category is None and args.category is None and len(rows) == total_target(),
        "seed": args.seed,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "category_counts": counts,
        "generator_version": "pivot-structured-v1",
        "elapsed_seconds": round(time.time() - started, 3),
        "provenance": "independent_targeted_generation_not_decisionpivot_rows",
    }
    args.out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "records": len(rows), "sha256": manifest["sha256"], "complete": manifest["complete"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
