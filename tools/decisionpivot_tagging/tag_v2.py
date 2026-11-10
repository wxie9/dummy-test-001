#!/usr/bin/env python3
"""Tag Kev v2 reconstruction rows with the DecisionPivot Core taxonomy.

The program is resumable. It appends one output row per input record and never
stores the API key. API calls contain a compact task fingerprint rather than the
full training row; long states are represented by head/tail excerpts.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parent
DEFAULT_TAXONOMY = ROOT / "taxonomy.json"
PROMPT_VERSION = "decisionpivot-tag-v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = limit * 2 // 3
    tail = limit - head
    return text[:head] + f"\n...[TRUNCATED {len(text) - limit} CHARS]...\n" + text[-tail:]


def compact(value: Any, limit: int) -> Any:
    if isinstance(value, str):
        return truncate_text(value, limit)
    rendered = canonical_json(value)
    if len(rendered) <= limit:
        return value
    return truncate_text(rendered, limit)


def question_view(row: dict[str, Any]) -> Any:
    if "questions" in row:
        out = {}
        for key, spec in row["questions"].items():
            if not isinstance(spec, dict):
                out[key] = spec
                continue
            out[key] = {k: spec[k] for k in ("type", "instructions", "criteria", "src") if k in spec}
        return out
    return {
        "question": row.get("question"),
        "kind": row.get("kind"),
        "options": row.get("options"),
    }


def meta_view(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
    keep = ("source", "dataset", "family", "subtype", "template", "variant", "generator", "selection_group")
    out = {k: meta[k] for k in keep if k in meta}
    for k in ("source", "variant", "selection_group"):
        if k in row:
            out[k] = row[k]
    return out


def row_id(row: dict[str, Any], fallback: str) -> str:
    meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
    return str(meta.get("id") or row.get("id") or fallback)


def fingerprint(row: dict[str, Any], key: str, state_chars: int) -> dict[str, Any]:
    return {
        "key": key,
        "state": compact(row.get("state"), state_chars),
        "questions": question_view(row),
        "metadata_hint": meta_view(row),
    }


def system_prompt(taxonomy: dict[str, Any]) -> str:
    lines = [
        "You classify training tasks by the decision capability they exercise, not by topic or answer label.",
        "Use exactly one primary DecisionPivot family and one allowed fine_category per item.",
        "Use other/other when no close Core analogue exists; never force an unrelated task into a family.",
        "Priority: answerability questions -> answerable_facts; access rights -> perm_inherit; ordered case policy -> policy_case; logs/counts -> log_count_check; bookings -> sched_conflict; action sequence to goal -> state_goal; function schema -> toolcall_valid; ranked queue -> triage_order; changed clause -> clause_change; package dependencies -> dep_resolve; transaction reconciliation -> ledger_reconcile; batch field rules -> record_rule; all-constraint search -> filter_match.",
        "Taxonomy:",
    ]
    for name, spec in taxonomy["families"].items():
        fine = ",".join(spec["fine_categories"])
        lines.append(f"{name} [layer {spec['layer']}]: {spec['description']} Fine=[{fine}]")
    lines.extend([
        "Return one JSON object with key `items`. Each output item must contain: key, family, fine_category, confidence (number 0..1), secondary_family (a family name or null), and rationale (max 18 words).",
        "Return every input key exactly once and no extra keys. Output JSON only.",
    ])
    return "\n".join(lines)


def call_api(url: str, api_key: str, model: str, prompt: str, items: list[dict[str, Any]], timeout: int, attempts: int) -> tuple[dict[str, Any], dict[str, Any]]:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": canonical_json({"items": items})},
        ],
        "temperature": 0,
        "max_tokens": max(256, len(items) * 110),
        "enable_thinking": False,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read())
            content = result["choices"][0]["message"]["content"]
            return json.loads(content), result.get("usage", {})
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            last_error = RuntimeError(f"HTTP {exc.code}: {raw[:500]}")
            if exc.code not in (408, 409, 429, 500, 502, 503, 504):
                raise last_error
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(min(30, (2 ** attempt) + random.random()))
    raise RuntimeError(f"API failed after {attempts} attempts: {last_error}")


def validate_response(payload: dict[str, Any], expected: list[str], taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("items")
    if not isinstance(rows, list):
        raise ValueError("response.items is not a list")
    by_key = {str(r.get("key")): r for r in rows if isinstance(r, dict)}
    if set(by_key) != set(expected):
        raise ValueError(f"response keys mismatch expected={len(expected)} actual={len(by_key)}")
    valid_families = taxonomy["families"]
    out = []
    for key in expected:
        row = by_key[key]
        family = row.get("family")
        if family not in valid_families:
            raise ValueError(f"invalid family {family!r}")
        fine = row.get("fine_category")
        if fine not in valid_families[family]["fine_categories"]:
            raise ValueError(f"invalid fine_category {family}/{fine}")
        confidence = float(row.get("confidence"))
        if not 0 <= confidence <= 1:
            raise ValueError(f"invalid confidence {confidence}")
        secondary = row.get("secondary_family")
        if secondary is not None and secondary not in valid_families:
            raise ValueError(f"invalid secondary_family {secondary!r}")
        out.append({
            "key": key,
            "family": family,
            "layer": valid_families[family]["layer"],
            "fine_category": fine,
            "confidence": confidence,
            "secondary_family": secondary,
            "rationale": str(row.get("rationale", ""))[:240],
        })
    return out


def parse_input(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--input must be NAME=/path/file.jsonl")
    name, path = value.split("=", 1)
    return name, Path(path)


def iter_rows(inputs: list[tuple[str, Path]], limit: Optional[int], per_input_limit: Optional[int], sample_seed: str) -> list[dict[str, Any]]:
    rows = []
    for dataset, path in inputs:
        source_rows = []
        with path.open() as handle:
            for line_no, line in enumerate(handle, 1):
                row = json.loads(line)
                rid = row_id(row, f"line-{line_no}")
                input_digest = digest(row)
                source_rows.append({
                    "dataset": dataset,
                    "source_path": str(path),
                    "line_no": line_no,
                    "record_id": rid,
                    "input_digest": input_digest,
                    "input_key": f"{dataset}:{line_no}:{input_digest[:16]}",
                    "row": row,
                })
        if per_input_limit is not None and len(source_rows) > per_input_limit:
            source_rows.sort(key=lambda r: hashlib.sha256(f"{sample_seed}:{r['input_key']}".encode()).hexdigest())
            source_rows = source_rows[:per_input_limit]
        rows.extend(source_rows)
        if limit is not None and len(rows) >= limit:
            return rows[:limit]
    return rows


def write_manifest(path: Path, args: argparse.Namespace, taxonomy: dict[str, Any], stats: dict[str, Any]) -> None:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "taxonomy_version": taxonomy["version"],
        "taxonomy_sha256": hashlib.sha256(DEFAULT_TAXONOMY.read_bytes()).hexdigest(),
        "model": args.model,
        "base_url": args.base_url,
        "inputs": [{"name": n, "path": str(p)} for n, p in args.input],
        "batch_size": args.batch_size,
        "concurrency": args.concurrency,
        "max_state_chars": args.max_state_chars,
        "limit": args.limit,
        "per_input_limit": args.per_input_limit,
        "sample_seed": args.sample_seed,
        "official_equivalence": False,
        "stats": stats,
        "updated_at_unix": time.time(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", type=parse_input, required=True, help="NAME=/path/file.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--model", default="qwen3.8-flash")
    parser.add_argument("--base-url", default="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    parser.add_argument("--api-key-env", default="DASHSCOPE_API_KEY")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-state-chars", type=int, default=3500)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--per-input-limit", type=int)
    parser.add_argument("--sample-seed", default="decisionpivot-tag-calibration-v1")
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing API key env {args.api_key_env}")
    taxonomy = json.loads(args.taxonomy.read_text())
    prompt = system_prompt(taxonomy)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "labels.jsonl"
    rejected_path = args.output_dir / "rejected.jsonl"
    manifest_path = args.output_dir / "manifest.json"

    completed: set[str] = set()
    if output_path.exists():
        with output_path.open() as handle:
            for line in handle:
                completed.add(json.loads(line)["input_key"])

    all_rows = iter_rows(args.input, args.limit, args.per_input_limit, args.sample_seed)
    pending = [r for r in all_rows if r["input_key"] not in completed]
    batches = [pending[i:i + args.batch_size] for i in range(0, len(pending), args.batch_size)]
    lock = threading.Lock()
    counters = Counter(completed=len(completed), pending=len(pending), batches=len(batches))
    usage = Counter()

    def run_batch(batch: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items = [fingerprint(r["row"], r["input_key"], args.max_state_chars) for r in batch]
        payload, used = call_api(args.base_url, api_key, args.model, prompt, items, args.timeout, args.attempts)
        labels = validate_response(payload, [r["input_key"] for r in batch], taxonomy)
        label_by_key = {r["key"]: r for r in labels}
        output = []
        for source in batch:
            label = label_by_key[source["input_key"]]
            output.append({
                "input_key": source["input_key"],
                "record_id": source["record_id"],
                "dataset": source["dataset"],
                "source_path": source["source_path"],
                "line_no": source["line_no"],
                "input_sha256": source["input_digest"],
                **{k: v for k, v in label.items() if k != "key"},
                "model": args.model,
                "prompt_version": PROMPT_VERSION,
                "taxonomy_version": taxonomy["version"],
            })
        return output, used

    started = time.time()
    with output_path.open("a") as output_handle, rejected_path.open("a") as rejected_handle:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            future_map = {pool.submit(run_batch, batch): batch for batch in batches}
            for future in concurrent.futures.as_completed(future_map):
                batch = future_map[future]
                try:
                    output, used = future.result()
                    with lock:
                        for row in output:
                            output_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                            counters[f"family:{row['family']}"] += 1
                        output_handle.flush()
                        counters["accepted"] += len(output)
                        counters["batches_done"] += 1
                        for key, value in used.items():
                            if isinstance(value, int):
                                usage[key] += value
                except Exception as exc:
                    with lock:
                        rejected_handle.write(json.dumps({
                            "input_keys": [r["input_key"] for r in batch],
                            "error": repr(exc),
                            "time": time.time(),
                        }, ensure_ascii=False) + "\n")
                        rejected_handle.flush()
                        counters["rejected_records"] += len(batch)
                        counters["failed_batches"] += 1
                done = counters["batches_done"] + counters["failed_batches"]
                if done and (done % 25 == 0 or done == len(batches)):
                    elapsed = max(time.time() - started, 1e-6)
                    print(json.dumps({
                        "batches": f"{done}/{len(batches)}",
                        "accepted": counters["accepted"],
                        "rejected_records": counters["rejected_records"],
                        "records_per_sec": round(counters["accepted"] / elapsed, 2),
                        "usage": dict(usage),
                    }, ensure_ascii=False), flush=True)
                    write_manifest(manifest_path, args, taxonomy, {**dict(counters), "usage": dict(usage)})

    write_manifest(manifest_path, args, taxonomy, {**dict(counters), "usage": dict(usage)})


if __name__ == "__main__":
    main()
