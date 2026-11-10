#!/usr/bin/env python3
"""Render Pivot structured scaffolds with DeepSeek and checkpoint accepted rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import atomic_write_jsonl, read_jsonl, validate_record  # noqa: E402
from llm_client import DEFAULT_BASE_URL, DEFAULT_MODEL, OpenAICompatClient  # noqa: E402
from pivot_llm_renderer import (  # noqa: E402
    SYSTEM_PROMPT,
    local_render_problems,
    materialize,
    parse_audit,
    parse_items,
    render_prompt,
    verification_prompt,
)


def _batch_render(scaffolds: Sequence[Mapping[str, Any]], client: OpenAICompatClient, verify: bool) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    response = client.complete_json(SYSTEM_PROMPT, render_prompt(scaffolds), temperature=0.75)
    rendered = parse_items(response)
    accepted = set()
    issues: Dict[str, List[str]] = {}
    for scaffold in scaffolds:
        item = rendered.get(scaffold["id"])
        local = ["missing_rendered_item"] if item is None else local_render_problems(scaffold, item)
        if local:
            issues[scaffold["id"]] = local
        else:
            accepted.add(scaffold["id"])
    if verify and accepted:
        candidates = [row for row in scaffolds if row["id"] in accepted]
        audit = client.complete_json(
            "You are a strict semantic-fidelity auditor. Return JSON only.",
            verification_prompt(candidates, rendered),
            temperature=0.0,
        )
        audited, audit_issues = parse_audit(audit)
        for scaffold in candidates:
            if scaffold["id"] not in audited:
                accepted.discard(scaffold["id"])
                issues[scaffold["id"]] = audit_issues.get(scaffold["id"], ["llm_fidelity_rejected"])

    output: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for scaffold in scaffolds:
        if scaffold["id"] not in accepted:
            rejected.append({"id": scaffold["id"], "reason": "render_rejected", "issues": issues.get(scaffold["id"], [])})
            continue
        try:
            output.append(materialize(scaffold, rendered[scaffold["id"]], client.model))
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({"id": scaffold["id"], "reason": "materialization_failed", "detail": str(exc)})
    return output, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("outputs/kev-v2-pivot-augmentation/structured.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("outputs/kev-v2-pivot-augmentation/rendered.jsonl"))
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, help="render only the first N missing scaffolds")
    parser.add_argument("--checkpoint-every", type=int, default=20)
    parser.add_argument("--verify", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if min(args.batch_size, args.concurrency, args.checkpoint_every) < 1:
        parser.error("batch size, concurrency and checkpoint interval must be positive")

    scaffolds = read_jsonl(args.input)
    scaffold_by_id = {row["id"]: row for row in scaffolds}
    existing = read_jsonl(args.out)
    accepted: Dict[str, Dict[str, Any]] = {}
    for row in existing:
        problems = validate_record(row)
        source_id = f"kev-pivot-augmentation-v1/{row['_meta']['pivot_category_id']}/{int(str(row['_meta']['id']).rsplit('/', 1)[-1]):06d}"
        if problems or source_id not in scaffold_by_id:
            raise ValueError(f"invalid existing rendered row {row.get('_meta', {}).get('id')}: {problems}")
        accepted[source_id] = row
    missing = [row for row in scaffolds if row["id"] not in accepted]
    if args.limit is not None:
        missing = missing[: args.limit]
    batches = [missing[pos:pos + args.batch_size] for pos in range(0, len(missing), args.batch_size)]
    client = OpenAICompatClient.from_env(model=args.model, base_url=args.base_url, api_key_env=args.api_key_env)
    rejected: List[Dict[str, Any]] = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(_batch_render, batch, client, args.verify): batch for batch in batches}
        for completed, future in enumerate(as_completed(futures), 1):
            batch = futures[future]
            try:
                made, failures = future.result()
            except Exception as exc:
                made = []
                failures = [{"id": row["id"], "reason": "api_batch_failed", "detail": f"{type(exc).__name__}: {exc}"} for row in batch]
            # Map by the structured hash instead of relying on batch order after rejects.
            hash_to_source = {row["_meta"]["state_sha256"]: row["id"] for row in batch}
            for row in made:
                accepted[hash_to_source[row["_meta"]["structured_state_sha256"]]] = row
            rejected.extend(failures)
            if completed % args.checkpoint_every == 0 or completed == len(batches):
                atomic_write_jsonl(args.out, [accepted[key] for key in sorted(accepted)])
                if rejected:
                    atomic_write_jsonl(args.out.with_suffix(".rejected.jsonl"), rejected)
            print(f"rendered {len(accepted)}/{len(scaffolds)}; attempted_batches={completed}/{len(batches)}", flush=True)

    payload = args.out.read_bytes() if args.out.exists() else b""
    manifest = {
        "structured_records": len(scaffolds),
        "rendered_records": len(accepted),
        "complete": len(accepted) == len(scaffolds),
        "model": client.model,
        "base_url": client.base_url,
        "verification_enabled": args.verify,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "elapsed_seconds": round(time.time() - started, 3),
        "credentials": f"environment variable {args.api_key_env}; not stored",
    }
    args.out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0 if not missing or len(accepted) == len(scaffolds) else 2


if __name__ == "__main__":
    raise SystemExit(main())
