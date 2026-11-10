#!/usr/bin/env python3
"""Finalize current DecisionPivot labels after the main Qwen tagging pass.

Non-moderated missing rows are retried with short request-local aliases so the
model cannot accidentally rewrite long input keys. Rows blocked by the API's
content filter receive an explicit, auditable source-level fallback. The script
then writes a current-input-only label file and a coverage report.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import tag_v2


OUTPUT_DIR = Path(
    "/data/kev/analysis/decisionpivot_taxonomy_qwen38flash_20261105/"
    "current_v2_candidates_run01"
)

INPUTS = [
    ("synthetic_abstention", Path("/data/kev-v2-public-reconstruction-20261104/generated/abstention.jsonl")),
    ("synthetic_intent", Path("/data/kev-v2-public-reconstruction-20261104/generated/intent.jsonl")),
    ("synthetic_long_doc", Path("/data/kev-v2-public-reconstruction-20261104/generated/long_doc.jsonl")),
    ("synthetic_numeric", Path("/data/kev-v2-public-reconstruction-20261104/generated/numeric.jsonl")),
    ("synthetic_retrieval", Path("/data/kev-v2-public-reconstruction-20261104/generated/retrieval.jsonl")),
    ("synthetic_rubric_judge", Path("/data/kev-v2-public-reconstruction-20261104/generated/rubric_judge.jsonl")),
    ("synthetic_tool_routing", Path("/data/kev-v2-public-reconstruction-20261104/generated/tool_routing.jsonl")),
    ("kev_hard_v1_extra_approx", Path("/data/kev-v2-public-reconstruction-20261104/generated/hard_v1_extra.jsonl")),
    ("kev_b1v2_exact", Path("/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/b1v2-train.jsonl")),
    ("kev_devtools_v1_raw", Path("/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/devtools-v1-train.jsonl")),
    ("kev_documents_v1_raw", Path("/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/documents-v1-train.jsonl")),
    ("kev_hard_v1_exact", Path("/data/kev-v2-public-reconstruction-20261102/kev_upstream_exact/hard-v1-train.jsonl")),
    ("tasksource_pivot24k", Path("/data/kev-v2-public-reconstruction-20261105/tasksource_pivot_selected/tasksource_pivot_commercial_24k_typed.jsonl")),
]


def output_row(source: dict, label: dict, model: str, method: str) -> dict:
    return {
        "input_key": source["input_key"],
        "record_id": source["record_id"],
        "dataset": source["dataset"],
        "source_path": source["source_path"],
        "line_no": source["line_no"],
        "input_sha256": source["input_digest"],
        "family": label["family"],
        "layer": label["layer"],
        "fine_category": label["fine_category"],
        "confidence": label["confidence"],
        "secondary_family": label.get("secondary_family"),
        "rationale": label["rationale"],
        "model": model,
        "label_method": method,
        "prompt_version": tag_v2.PROMPT_VERSION,
        "taxonomy_version": "decisionpivot-core-v1.1-alignment-v1",
    }


def source_fallback(source: dict) -> dict:
    record_id = str(source["record_id"])
    dataset = source["dataset"]
    meta = tag_v2.meta_view(source["row"])
    if dataset == "kev_devtools_v1_raw" and record_id.startswith("aegis/"):
        return {
            "family": "other",
            "layer": "Other",
            "fine_category": "other",
            "confidence": 0.92,
            "secondary_family": "policy_case",
            "rationale": "Aegis safety classification has no close DecisionPivot Core analogue.",
        }
    if dataset == "synthetic_rubric_judge":
        return {
            "family": "other",
            "layer": "Other",
            "fine_category": "other",
            "confidence": 0.99,
            "secondary_family": None,
            "rationale": "Rubric judging is outside the DecisionPivot Core families.",
        }
    task_source = str(meta.get("source", ""))
    if task_source == "agent_action_safety":
        return {
            "family": "perm_inherit",
            "layer": "B",
            "fine_category": "explicit_deny",
            "confidence": 0.82,
            "secondary_family": "policy_case",
            "rationale": "Agent action safety primarily tests explicit permission denial.",
        }
    if task_source == "tabfact":
        return {
            "family": "answerable_facts",
            "layer": "A",
            "fine_category": "direct_lookup",
            "confidence": 0.60,
            "secondary_family": "record_rule",
            "rationale": "TabFact tests whether a table supports a factual statement.",
        }
    if task_source == "probability_words_nli/reasoning_2hop":
        return {
            "family": "answerable_facts",
            "layer": "A",
            "fine_category": "multihop_fact_chain",
            "confidence": 0.70,
            "secondary_family": "policy_case",
            "rationale": "Two-hop NLI requires resolving a short fact chain.",
        }
    raise RuntimeError(f"no audited fallback for {source['input_key']}")


def main() -> None:
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit("missing DASHSCOPE_API_KEY")
    taxonomy = json.loads(tag_v2.DEFAULT_TAXONOMY.read_text())
    prompt = tag_v2.system_prompt(taxonomy)
    rows = tag_v2.iter_rows(INPUTS, None, None, "decisionpivot-tag-calibration-v1")
    current = {row["input_key"]: row for row in rows}

    labels_path = OUTPUT_DIR / "labels.jsonl"
    labels: dict[str, dict] = {}
    with labels_path.open() as handle:
        for line in handle:
            row = json.loads(line)
            labels[row["input_key"]] = row

    missing = [current[key] for key in sorted(set(current) - set(labels))]
    audit = []
    appended = []
    for index, source in enumerate(missing, 1):
        alias = f"item-{index:03d}"
        item = tag_v2.fingerprint(source["row"], alias, 3500)
        method = "qwen3.8-flash-alias-retry"
        try:
            payload, _ = tag_v2.call_api(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                api_key,
                "qwen3.8-flash",
                prompt,
                [item],
                90,
                3,
            )
            label = tag_v2.validate_response(payload, [alias], taxonomy)[0]
            model = "qwen3.8-flash"
            result = output_row(source, label, model, method)
        except Exception as exc:
            label = source_fallback(source)
            method = "audited-source-fallback-v1"
            result = output_row(source, label, "deterministic-fallback-v1", method)
            audit.append({
                "input_key": source["input_key"],
                "record_id": source["record_id"],
                "dataset": source["dataset"],
                "fallback_reason": repr(exc)[:1000],
                "assigned_family": label["family"],
                "assigned_fine_category": label["fine_category"],
            })
        labels[result["input_key"]] = result
        appended.append(result)

    if appended:
        with labels_path.open("a") as handle:
            for row in appended:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    current_path = OUTPUT_DIR / "labels_current.jsonl"
    with current_path.open("w") as handle:
        for source in rows:
            handle.write(json.dumps(labels[source["input_key"]], ensure_ascii=False) + "\n")

    audit_path = OUTPUT_DIR / "fallback_audit.jsonl"
    with audit_path.open("w") as handle:
        for row in audit:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    method_counts = Counter(row.get("label_method", "qwen3.8-flash-main") for row in labels.values() if row["input_key"] in current)
    family_counts = Counter(labels[key]["family"] for key in current)
    report = {
        "current_input_rows": len(rows),
        "current_unique_keys": len(current),
        "covered_current_keys": sum(key in labels for key in current),
        "missing_current_keys": [key for key in current if key not in labels],
        "stale_keys_excluded_from_labels_current": len(set(labels) - set(current)),
        "finalization_missing_before": len(missing),
        "finalization_qwen_alias_retry": sum(row.get("label_method") == "qwen3.8-flash-alias-retry" for row in appended),
        "finalization_audited_fallback": len(audit),
        "label_method_counts": dict(method_counts),
        "family_counts": dict(family_counts),
    }
    (OUTPUT_DIR / "coverage_final.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
