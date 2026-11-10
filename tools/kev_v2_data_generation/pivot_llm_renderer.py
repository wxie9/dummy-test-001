#!/usr/bin/env python3
"""DeepSeek rendering and verification for solver-labelled Pivot scaffolds."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple

try:
    from .common import build_record
except ImportError:
    from common import build_record


SYSTEM_PROMPT = """You render synthetic decision-training data from a machine-checked scaffold.
Return JSON only. Do not solve or relabel the problem. Preserve every fact, number,
boundary, logical connective, exception, unit, graph edge, operation order, and
semantic option meaning. Write clear natural English. Do not mention the category,
gold answer, solver, scaffold, benchmark, or generation process."""


def render_prompt(scaffolds: Sequence[Mapping[str, Any]]) -> str:
    compact = []
    for row in scaffolds:
        compact.append({
            "id": row["id"],
            "state": row["state"],
            "question_intent": row["question_spec"]["intent"],
            "semantic_options": row["question_spec"]["semantic_options"],
        })
    return f"""Render each scaffold as one self-contained multiple-choice decision problem.

For each item return:
- id: copied exactly
- context: natural-language presentation of all state facts; tables/lists are allowed
- question: one direct question implementing question_intent
- options: an object with exactly the same option keys; express each semantic value naturally

Do not add facts. Do not remove facts needed to solve the question. Do not expose the answer.
Return one JSON object with shape {{"items": [{{"id": ..., "context": ..., "question": ..., "options": {{...}}}}]}}.

SCAFFOLDS:
{json.dumps(compact, ensure_ascii=False, separators=(',', ':'))}
"""


def parse_items(response: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    items = response.get("items")
    if not isinstance(items, list):
        if all(key in response for key in ("id", "context", "question", "options")):
            items = [response]
        else:
            raise ValueError("render response must contain an items list")
    result: Dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            continue
        result[item["id"]] = item
    return result


def local_render_problems(scaffold: Mapping[str, Any], rendered: Mapping[str, Any]) -> List[str]:
    problems: List[str] = []
    if rendered.get("id") != scaffold["id"]:
        problems.append("id_mismatch")
    for field in ("context", "question"):
        if not isinstance(rendered.get(field), str) or not rendered[field].strip():
            problems.append(f"missing_{field}")
    options = rendered.get("options")
    expected_keys = set(scaffold["question_spec"]["semantic_options"])
    if not isinstance(options, Mapping):
        problems.append("options_not_object")
    else:
        if set(options) != expected_keys:
            problems.append("option_key_mismatch")
        for key, value in options.items():
            if value is None or isinstance(value, (dict, list)) or (isinstance(value, str) and not value.strip()):
                problems.append(f"empty_option_{key}")
    return problems


def verification_prompt(scaffolds: Sequence[Mapping[str, Any]], rendered: Mapping[str, Mapping[str, Any]]) -> str:
    payload = []
    for scaffold in scaffolds:
        payload.append({
            "id": scaffold["id"],
            "state": scaffold["state"],
            "question_intent": scaffold["question_spec"]["intent"],
            "semantic_options": scaffold["question_spec"]["semantic_options"],
            "rendered": rendered.get(scaffold["id"]),
        })
    return f"""Audit each rendered item against its scaffold.
Mark faithful=false if any fact, number, boundary, AND/OR relation, exception, unit,
edge, operation order, question meaning, or option meaning changed or was omitted.
The prose may reorder information and use synonyms. Do not judge the gold answer.

Return JSON only:
{{"items":[{{"id":"...","faithful":true,"issues":[]}}]}}

ITEMS:
{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}
"""


def parse_audit(response: Mapping[str, Any]) -> Tuple[set[str], Dict[str, List[str]]]:
    accepted: set[str] = set()
    issues: Dict[str, List[str]] = {}
    items = response.get("items", [response] if "id" in response else [])
    if not isinstance(items, list):
        return accepted, issues
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            continue
        item_issues = item.get("issues", [])
        if not isinstance(item_issues, list):
            item_issues = [str(item_issues)]
        if item.get("faithful") is True:
            accepted.add(item["id"])
        else:
            issues[item["id"]] = [str(value) for value in item_issues]
    return accepted, issues


def materialize(scaffold: Mapping[str, Any], rendered: Mapping[str, Any], model: str) -> Dict[str, Any]:
    problems = local_render_problems(scaffold, rendered)
    if problems:
        raise ValueError(",".join(problems))
    meta = scaffold["_meta"]
    return build_record(
        scaffold["category_id"],
        int(meta["index"]),
        {"context": rendered["context"]},
        rendered["question"],
        {key: str(value) for key, value in rendered["options"].items()},
        scaffold["question_spec"]["label"],
        seed=int(meta["seed"]),
        generator="pivot_structured_solver_plus_deepseek_renderer_v1",
        dataset="pivot-augmentation-v1",
        extra_meta={
            "family": scaffold["family"],
            "pivot_category_id": scaffold["category_id"],
            "pivot_category_zh": scaffold["category_zh"],
            "structured_state_sha256": meta["state_sha256"],
            "render_model": model,
            "semantic_answer_value": scaffold["question_spec"]["answer_value"],
        },
    )
