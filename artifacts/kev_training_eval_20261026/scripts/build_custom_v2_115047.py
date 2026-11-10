#!/usr/bin/env python3
"""Build the auditable 115,047-record custom Kev-v2 candidate training file.

This is a public reconstruction, not the unreleased official Kev-v2 corpus.
It combines:
  * 71,047 Kev-shaped public/self-generated records;
  * 24,000 selected Tasksource typed decisions, converted to Kev request shape;
  * 20,000 DecisionPivot-targeted records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


OLD_INPUTS = [
    "generated/abstention.jsonl",
    "generated/intent.jsonl",
    "generated/long_doc.jsonl",
    "generated/numeric.jsonl",
    "generated/retrieval.jsonl",
    "generated/rubric_judge.jsonl",
    "generated/tool_routing.jsonl",
    "generated/hard_v1_extra.jsonl",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_digest(record: dict[str, Any]) -> str:
    payload = {
        "state": record["state"],
        "questions": record["questions"],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                yield line_no, json.loads(line)


def validate_kev(record: dict[str, Any], where: str) -> None:
    if "state" not in record:
        raise ValueError(f"{where}: missing state")
    questions = record.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError(f"{where}: questions must be a non-empty object")
    for qid, q in questions.items():
        kind = q.get("type")
        if kind not in {"choice", "noul", "score"}:
            raise ValueError(f"{where}:{qid}: unsupported type {kind!r}")
        if "instructions" not in q or "label" not in q:
            raise ValueError(f"{where}:{qid}: missing instructions/label")
        if kind == "choice":
            criteria = q.get("criteria")
            if not isinstance(criteria, dict) or q["label"] not in criteria:
                raise ValueError(f"{where}:{qid}: invalid choice criteria/label")
        elif kind == "noul" and not isinstance(q["label"], bool):
            raise ValueError(f"{where}:{qid}: noul label must be bool")
        elif kind == "score":
            criteria = q.get("criteria")
            if not isinstance(criteria, list) or not (0 <= int(q["label"]) < len(criteria)):
                raise ValueError(f"{where}:{qid}: invalid score criteria/label")


def convert_tasksource(row: dict[str, Any], line_no: int) -> dict[str, Any]:
    kind = row["kind"]
    values = [float(v) for v in row["target"]]
    if not values:
        raise ValueError(f"tasksource:{line_no}: empty target")
    q: dict[str, Any] = {
        "type": kind,
        "instructions": row["question"],
        "src": f"tasksource/{row['source']}",
    }

    if kind == "choice":
        options = list(row["options"])
        if len(options) != len(values) or len(options) < 2:
            raise ValueError(f"tasksource:{line_no}: bad choice options/target")
        keys = [f"opt_{i}" for i in range(len(options))]
        q["criteria"] = dict(zip(keys, options))
        best = max(range(len(values)), key=values.__getitem__)
        q["label"] = keys[best]
        q["target"] = {key: value for key, value in zip(keys, values)}
    elif kind == "noul":
        if len(values) != 1 or not (0.0 <= values[0] <= 1.0):
            raise ValueError(f"tasksource:{line_no}: bad noul target")
        probability_true = values[0]
        q["criteria"] = {"false": "No", "true": "Yes"}
        q["label"] = probability_true >= 0.5
        q["target"] = {"false": 1.0 - probability_true, "true": probability_true}
    elif kind == "score":
        levels = list(row["options"])
        if len(levels) != len(values) or len(levels) < 2:
            raise ValueError(f"tasksource:{line_no}: bad score levels/target")
        q["criteria"] = levels
        q["label"] = max(range(len(values)), key=values.__getitem__)
        q["target"] = {str(i): value for i, value in enumerate(values)}
    else:
        raise ValueError(f"tasksource:{line_no}: unsupported kind {kind!r}")

    record_id = str(row["id"])
    return {
        "state": row["state"],
        "questions": {str(row.get("question_id") or "decision"): q},
        "_meta": {
            "id": f"tasksource-pivot24k/{record_id}",
            "group_id": f"tasksource-pivot24k/{row.get('group_id') or record_id}",
            "source": f"tasksource/{row['source']}",
            "dataset": "tasksource-pivot-commercial-24k",
            "split": "train",
            "variant": str(row.get("variant") or "clean"),
            "license": row.get("license"),
            "license_use": row.get("license_use"),
            "selection_group": row.get("selection_group"),
            "selection_digest": row.get("selection_digest"),
            "provenance": "public_tasksource_selection_not_official_kev_v2_rows",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-root", type=Path, required=True)
    ap.add_argument("--upstream-root", type=Path, required=True)
    ap.add_argument("--tasksource", type=Path, required=True)
    ap.add_argument("--pivot", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--drop-exact-duplicates", action="store_true")
    args = ap.parse_args()

    upstream = [
        args.upstream_root / "b1v2-train.jsonl",
        args.upstream_root / "devtools-v1-train.jsonl",
        args.upstream_root / "documents-v1-train.jsonl",
        args.upstream_root / "hard-v1-train.jsonl",
    ]
    inputs = [("kev_corpus", args.generated_root.parent / rel) for rel in OLD_INPUTS]
    inputs.extend(("kev_corpus", p) for p in upstream)
    inputs.append(("pivot_targeted", args.pivot))
    for _, path in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not args.tasksource.is_file():
        raise FileNotFoundError(args.tasksource)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    candidate_counts: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    question_types: Counter[str] = Counter()
    ids: set[str] = set()
    duplicate_ids: list[str] = []
    content_seen: set[str] = set()
    exact_content_duplicates = 0
    emitted_records = 0
    source_info: list[dict[str, Any]] = []

    def emit(
        out,
        record: dict[str, Any],
        component: str,
        namespace: str,
        line_no: int,
        where: str,
    ) -> None:
        nonlocal exact_content_duplicates, emitted_records
        validate_kev(record, where)
        meta = record.setdefault("_meta", {})
        original_id = str(meta.get("id") or line_no)
        original_group_id = str(meta.get("group_id") or original_id)
        # Some released upstream files reuse IDs across partitions or variants.
        # Preserve those IDs as provenance, while giving every training row an
        # unambiguous, deterministic ID scoped by source and line number.
        meta["original_id"] = original_id
        meta["original_group_id"] = original_group_id
        meta["id"] = f"{namespace}/{line_no:06d}/{original_id}"
        meta["group_id"] = f"{namespace}/{original_group_id}"
        record_id = meta["id"]
        if record_id in ids:
            duplicate_ids.append(record_id)
        ids.add(record_id)
        candidate_counts[component] += 1
        digest = normalized_digest(record)
        if digest in content_seen:
            exact_content_duplicates += 1
            if args.drop_exact_duplicates:
                return
        content_seen.add(digest)
        counts[component] += 1
        for q in record["questions"].values():
            question_types[q["type"]] += 1
        out.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        emitted_records += 1

    with args.output.open("w", encoding="utf-8") as out:
        for component, path in inputs:
            before_candidates = candidate_counts[component]
            before = counts[component]
            for line_no, record in iter_jsonl(path):
                namespace = f"{component}/{path.stem}"
                emit(out, record, component, namespace, line_no, f"{path}:{line_no}")
            source_info.append({
                "component": component,
                "path": str(path),
                "candidate_records": candidate_counts[component] - before_candidates,
                "records": counts[component] - before,
                "sha256": sha256_file(path),
            })

        before_candidates = candidate_counts["tasksource"]
        before = counts["tasksource"]
        for line_no, row in iter_jsonl(args.tasksource):
            record = convert_tasksource(row, line_no)
            emit(
                out,
                record,
                "tasksource",
                "tasksource/pivot-commercial-24k",
                line_no,
                f"{args.tasksource}:{line_no}",
            )
        source_info.append({
            "component": "tasksource",
            "path": str(args.tasksource),
            "candidate_records": candidate_counts["tasksource"] - before_candidates,
            "records": counts["tasksource"] - before,
            "sha256": sha256_file(args.tasksource),
        })

    total = sum(candidate_counts.values())
    expected = {"kev_corpus": 71047, "tasksource": 24000, "pivot_targeted": 20000}
    if dict(candidate_counts) != expected:
        raise ValueError(f"candidate component counts {dict(candidate_counts)} != {expected}")
    if total != 115047:
        raise ValueError(f"total {total} != 115047")
    if duplicate_ids:
        raise ValueError(f"duplicate IDs: {duplicate_ids[:20]}")

    manifest = {
        "name": "kev-v2-custom-public-candidate-115047",
        "official_equivalence": False,
        "warning": "Public/self-generated reconstruction; not the private official Kev-v2 training corpus.",
        "candidate_records": total,
        "records": emitted_records,
        "candidate_component_counts": dict(candidate_counts),
        "component_counts": dict(counts),
        "question_type_counts": dict(question_types),
        "unique_ids": len(ids),
        "unique_content": len(content_seen),
        "exact_content_duplicates": exact_content_duplicates,
        "drop_exact_duplicates": args.drop_exact_duplicates,
        "output": str(args.output),
        "output_sha256": sha256_file(args.output),
        "sources": source_info,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
