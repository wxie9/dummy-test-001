#!/usr/bin/env python3
"""Generate solver-labelled public reconstructions of Kev synthetic-v1 and hard-v1-extra."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import atomic_write_jsonl, read_jsonl, validate_record  # noqa: E402
from llm_client import DEFAULT_BASE_URL, DEFAULT_MODEL, OpenAICompatClient  # noqa: E402
from llm_generators import (  # noqa: E402
    LLM_FAMILIES,
    SYSTEM_PROMPT,
    faithful_ids,
    make_scaffold,
    materialize,
    render_prompt,
    response_items,
    verification_prompt,
)
from rule_generators import RULE_FAMILIES, generate_rule_record  # noqa: E402


TARGETS = {
    "abstention": 3530,
    "intent": 4848,
    "long_doc": 6042,
    "numeric": 3684,
    "retrieval": 2772,
    "rubric_judge": 7288,
    "tool_routing": 5514,
    "hard_v1_extra": 6000,
}


def record_index(record: Mapping[str, Any]) -> int:
    return int(str(record["_meta"]["id"]).rsplit("/", 1)[-1])


def validate_existing(path: Path, family: str) -> Dict[int, Dict[str, Any]]:
    result: Dict[int, Dict[str, Any]] = {}
    ids = set()
    state_hashes = set()
    for record in read_jsonl(path):
        problems = validate_record(record)
        if problems:
            raise ValueError(f"{path}: invalid existing record: {'; '.join(problems)}")
        if record["_meta"]["family"] != family:
            raise ValueError(f"{path}: mixed family {record['_meta']['family']} in {family} output")
        idx = record_index(record)
        record_id = record["_meta"]["id"]
        state_hash = record["_meta"]["state_sha256"]
        if idx in result or record_id in ids or state_hash in state_hashes:
            raise ValueError(f"{path}: duplicate index, id, or state hash")
        result[idx] = record
        ids.add(record_id)
        state_hashes.add(state_hash)
    return result


def generate_rules(family: str, count: int, seed: int, existing: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    output = dict(existing)
    for index in range(count):
        if index not in output:
            output[index] = generate_rule_record(family, index, seed)
    return output


def _llm_batch(
    family: str,
    indices: Sequence[int],
    seed: int,
    client: OpenAICompatClient,
    verify: bool,
) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    scaffolds = [make_scaffold(family, index, seed) for index in indices]
    prompt = render_prompt(family, scaffolds)
    response = client.complete_json(SYSTEM_PROMPT, prompt)
    items = response_items(response)
    accepted_ids = {scaffold["id"] for scaffold in scaffolds}
    rejected: List[Dict[str, Any]] = []
    if verify:
        audit = client.complete_json(
            "You are a strict data-generation verifier. Return JSON only.",
            verification_prompt(family, scaffolds, response),
            temperature=0.0,
        )
        accepted_ids, issues = faithful_ids(audit)
        for scaffold in scaffolds:
            if scaffold["id"] not in accepted_ids:
                rejected.append({"id": scaffold["id"], "reason": "llm_verification_failed", "issues": issues.get(scaffold["id"], [])})

    output: Dict[int, Dict[str, Any]] = {}
    for index, scaffold in zip(indices, scaffolds):
        item = items.get(scaffold["id"])
        if item is None:
            rejected.append({"id": scaffold["id"], "reason": "missing_rendered_item"})
            continue
        if scaffold["id"] not in accepted_ids:
            continue
        try:
            output[index] = materialize(family, scaffold, item, index, seed, client.model)
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({"id": scaffold["id"], "reason": "materialization_failed", "detail": str(exc)})
    return output, rejected


def generate_llm(
    family: str,
    count: int,
    seed: int,
    existing: Dict[int, Dict[str, Any]],
    client: OpenAICompatClient,
    batch_size: int,
    concurrency: int,
    verify: bool,
    max_rounds: int,
    checkpoint_path: Optional[Path] = None,
    checkpoint_every: int = 25,
) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    output = dict(existing)
    rejected: List[Dict[str, Any]] = []
    for round_no in range(max_rounds):
        missing = [index for index in range(count) if index not in output]
        if not missing:
            break
        batches = [missing[pos : pos + batch_size] for pos in range(0, len(missing), batch_size)]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_llm_batch, family, batch, seed, client, verify): batch
                for batch in batches
            }
            completed_batches = 0
            for future in as_completed(futures):
                batch = futures[future]
                try:
                    made, failures = future.result()
                except Exception as exc:  # keep other batches and checkpoint their progress
                    made = {}
                    failures = [
                        {
                            "id": make_scaffold(family, index, seed)["id"],
                            "reason": "batch_api_failed",
                            "detail": f"{type(exc).__name__}: {exc}",
                        }
                        for index in batch
                    ]
                state_hashes = {record["_meta"]["state_sha256"] for record in output.values()}
                for index, record in sorted(made.items()):
                    state_hash = record["_meta"]["state_sha256"]
                    if state_hash in state_hashes:
                        failures.append({"id": record["_meta"]["id"], "reason": "duplicate_state"})
                        continue
                    output[index] = record
                    state_hashes.add(state_hash)
                for failure in failures:
                    failure["round"] = round_no + 1
                rejected.extend(failures)
                completed_batches += 1
                if checkpoint_path is not None and completed_batches % checkpoint_every == 0:
                    atomic_write_jsonl(checkpoint_path, [output[index] for index in sorted(output)])
                    if rejected:
                        atomic_write_jsonl(checkpoint_path.with_suffix(".rejected.jsonl"), rejected)
                print(f"{family}: {len(output)}/{count}", flush=True)
            if checkpoint_path is not None:
                atomic_write_jsonl(checkpoint_path, [output[index] for index in sorted(output)])
                if rejected:
                    atomic_write_jsonl(checkpoint_path.with_suffix(".rejected.jsonl"), rejected)
    return output, rejected


def write_manifest(path: Path, family: str, count: int, records: Sequence[Mapping[str, Any]], args: argparse.Namespace, started: float) -> None:
    payload = path.read_bytes()
    manifest = {
        "family": family,
        "records": len(records),
        "target_records": count,
        "complete": len(records) == count,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "seed": args.seed,
        "generator_version": "kev-public-reconstruction-v1",
        "official_equivalence": False,
        "provenance": "independent public reconstruction; not official Kev rows",
        "llm": None if family in RULE_FAMILIES else {
            "provider_protocol": "OpenAI-compatible chat/completions",
            "model": args.model,
            "base_url": args.base_url,
            "api_key_env": args.api_key_env,
            "verification_enabled": args.verify_llm,
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    manifest_path = path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_family(args: argparse.Namespace, family: str, count: int) -> int:
    started = time.time()
    out_path = args.out_dir / f"{family}.jsonl"
    existing = validate_existing(out_path, family)
    if any(index >= count for index in existing):
        raise ValueError(f"{out_path} contains indices outside requested count {count}")
    if family in RULE_FAMILIES:
        output = generate_rules(family, count, args.seed, existing)
        rejected: List[Dict[str, Any]] = []
    else:
        client = OpenAICompatClient.from_env(model=args.model, base_url=args.base_url, api_key_env=args.api_key_env)
        output, rejected = generate_llm(
            family, count, args.seed, existing, client,
            args.batch_size, args.concurrency, args.verify_llm, args.max_rounds,
            checkpoint_path=out_path, checkpoint_every=args.checkpoint_every,
        )
    records = [output[index] for index in sorted(output)]
    if len({record["_meta"]["id"] for record in records}) != len(records):
        raise ValueError(f"{family}: duplicate record ids after generation")
    if len({record["_meta"]["state_sha256"] for record in records}) != len(records):
        raise ValueError(f"{family}: duplicate state hashes after generation")
    atomic_write_jsonl(out_path, records)
    if rejected:
        rejected_path = out_path.with_suffix(".rejected.jsonl")
        atomic_write_jsonl(rejected_path, rejected)
    write_manifest(out_path, family, count, records, args, started)
    print(f"wrote {len(records)}/{count} {family} records to {out_path}")
    return 0 if len(records) == count else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--family", choices=sorted(TARGETS))
    group.add_argument("--all", action="store_true", help="generate every family at its disclosed target count")
    parser.add_argument("--count", type=int, help="override target count; only valid with --family")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/kev-v2-public-reconstruction/synthetic-v1"))
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--checkpoint-every", type=int, default=25, help="persist accepted rows after this many completed API batches")
    parser.add_argument("--verify-llm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true", help="print one LLM prompt or validate one rule record without writing")
    args = parser.parse_args()
    if args.count is not None and args.all:
        parser.error("--count is only valid with --family")
    if args.batch_size < 1 or args.concurrency < 1 or args.max_rounds < 1 or args.checkpoint_every < 1:
        parser.error("batch size, concurrency, max rounds, and checkpoint interval must be positive")
    families = sorted(TARGETS) if args.all else [args.family]
    if args.dry_run:
        for family in families:
            if family in RULE_FAMILIES:
                print(json.dumps(generate_rule_record(family, 0, args.seed), ensure_ascii=False, indent=2))
            else:
                print(f"# {family}\n{render_prompt(family, [make_scaffold(family, 0, args.seed)])}")
        return 0
    status = 0
    for family in families:
        target = args.count if args.count is not None else TARGETS[family]
        status |= generate_family(args, family, target)
    return status


if __name__ == "__main__":
    raise SystemExit(main())

