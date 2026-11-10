#!/usr/bin/env python3
"""Audit schema, duplicates, label balance, and optional held-out 8-gram overlap."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import canonical_json, read_jsonl, validate_record  # noqa: E402


TOKEN = re.compile(r"[A-Za-z0-9_]+")


def text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    return canonical_json(value)


def ngrams(text: str, n: int = 8) -> Set[Tuple[str, ...]]:
    tokens = [token.casefold() for token in TOKEN.findall(text)]
    return {tuple(tokens[pos : pos + n]) for pos in range(max(0, len(tokens) - n + 1))}


def heldout_ngrams(paths: Sequence[Path]) -> Set[Tuple[str, ...]]:
    result: Set[Tuple[str, ...]] = set()
    for path in paths:
        for row in read_jsonl(path):
            result.update(ngrams(text_of(row.get("state"))))
            for question in (row.get("questions") or {}).values():
                result.update(ngrams(text_of(question.get("instructions", ""))))
    return result


def audit(path: Path, heldout: Sequence[Path]) -> Dict[str, Any]:
    records = read_jsonl(path)
    problems: List[Dict[str, Any]] = []
    ids = collections.Counter()
    state_hashes = collections.Counter()
    labels: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    reference_grams = heldout_ngrams(heldout) if heldout else set()
    overlaps = []
    for index, record in enumerate(records):
        for problem in validate_record(record):
            problems.append({"index": index, "id": record.get("_meta", {}).get("id"), "problem": problem})
        meta = record.get("_meta") or {}
        ids[str(meta.get("id"))] += 1
        state_hashes[str(meta.get("state_sha256"))] += 1
        for qid, question in (record.get("questions") or {}).items():
            labels[qid][str(question.get("label"))] += 1
        if reference_grams:
            shared = ngrams(text_of(record.get("state"))) & reference_grams
            if shared:
                overlaps.append({"id": meta.get("id"), "shared_8grams": len(shared)})
    duplicate_ids = sorted(key for key, count in ids.items() if count > 1)
    duplicate_states = sorted(key for key, count in state_hashes.items() if count > 1)
    report = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "records": len(records),
        "schema_problems": problems,
        "duplicate_ids": duplicate_ids,
        "duplicate_state_hashes": duplicate_states,
        "label_counts": {qid: dict(counter) for qid, counter in sorted(labels.items())},
        "heldout_files": [str(path) for path in heldout],
        "heldout_8gram_overlaps": overlaps,
        "passed": not problems and not duplicate_ids and not duplicate_states and not overlaps,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--heldout", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit(args.jsonl, args.heldout)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

