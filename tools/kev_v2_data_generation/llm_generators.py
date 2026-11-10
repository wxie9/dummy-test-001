#!/usr/bin/env python3
"""Program-scaffolded LLM rendering for four language-heavy data families."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple

try:
    from .common import build_record, shuffled_options, stable_rng
except ImportError:
    from common import build_record, shuffled_options, stable_rng


LLM_FAMILIES = ("intent", "long_doc", "rubric_judge", "hard_v1_extra")

INTENTS = {
    "cancel_subscription": "Cancel an existing subscription",
    "change_delivery_address": "Change the delivery address for an order",
    "track_order": "Check the shipment status of an order",
    "request_refund": "Ask for money back for a completed purchase",
    "report_fraud": "Report suspected unauthorized or fraudulent activity",
    "reset_credentials": "Recover or reset account credentials",
    "update_payment_method": "Replace or update a stored payment method",
    "general_information": "Ask a general informational question without requesting an account action",
}


def _policy_scaffold(index: int, seed: int, family: str) -> Dict[str, Any]:
    rng = stable_rng(seed, family, index)
    record_count = rng.randrange(1, 1500)
    exports = rng.randrange(0, 7)
    verified = rng.choice([True, False])
    legal_hold = rng.choice([True, False])
    region = rng.choice(["Branzim", "Caldria", "Dovara"])
    case = {
        "record_count": record_count,
        "exports_last_30_days": exports,
        "requester_verified": verified,
        "legal_hold": legal_hold,
        "data_region": region,
    }
    # Ordered rules with an explicit exception. The program, not the LLM, computes the answer.
    if not verified and exports >= 3:
        label = "deny"
        decisive = "unverified_high_export_count"
    elif legal_hold and region != "Branzim" and exports > 3:
        label = "deny"
        decisive = "legal_hold_foreign_region_high_exports"
    elif legal_hold and record_count >= 100:
        label = "escalate"
        decisive = "legal_hold_without_small_export_exception"
    elif exports < 2 and record_count < 500:
        label = "approve"
        decisive = "low_frequency_small_export"
    else:
        label = "escalate"
        decisive = "default_review"
    return {
        "id": f"{family}-{index:06d}",
        "rules": [
            "Deny if the requester is unverified and exports in the last 30 days are at least 3.",
            "Deny if a legal hold exists, the data region is not Branzim, and exports are greater than 3.",
            "Escalate when a legal hold exists, except that this rule does not apply when fewer than 100 records are requested.",
            "Approve when exports are fewer than 2 and fewer than 500 records are requested.",
            "Otherwise escalate for manual review.",
        ],
        "case": case,
        "semantic_label": label,
        "decisive_rule": decisive,
        "style": rng.choice(["enterprise policy", "compliance handbook", "operations manual", "data export standard"]),
    }


def make_scaffold(family: str, index: int, seed: int) -> Dict[str, Any]:
    rng = stable_rng(seed, family, index)
    if family == "intent":
        intent = list(INTENTS)[index % len(INTENTS)]
        return {
            "id": f"intent-{index:06d}",
            "intent": intent,
            "intent_definition": INTENTS[intent],
            "entities": {
                "order_id": f"ORD-{rng.randrange(10000, 99999)}",
                "channel": rng.choice(["chat", "email", "mobile support"]),
                "urgency": rng.choice(["normal", "urgent", "not stated"]),
            },
            "style": rng.choice(["concise", "colloquial", "indirect", "contains a harmless typo", "two-sentence follow-up"]),
            "semantic_label": intent,
        }
    if family == "long_doc":
        scaffold = _policy_scaffold(index, seed, family)
        scaffold["target_words"] = rng.choice([900, 1200, 1600, 2200])
        scaffold["distractor_sections"] = rng.sample(
            ["definitions", "retention", "billing", "incident response", "appeals", "audit logging"], 3
        )
        return scaffold
    if family == "rubric_judge":
        facts = {
            # The first version only varied status/date/refund, which caps the
            # number of distinct states at 2,016.  The disclosed target is
            # 7,288, so deterministic case attributes are also required.
            "case_id": f"CASE-{index:06d}",
            "order_id": f"ORD-{rng.randrange(100000, 999999)}",
            "carrier": rng.choice(["Aster", "BlueRail", "Cinder", "Dovetail"]),
            "service_level": rng.choice(["standard", "priority", "overnight"]),
            "destination_region": rng.choice(["north", "south", "east", "west"]),
            "shipment_status": rng.choice(["in transit", "delayed", "delivered"]),
            "promised_date": f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "refund_allowed": rng.choice([True, False]),
        }
        winner = rng.choice(["candidate_1", "candidate_2", "candidate_3"])
        defects = {
            key: ([] if key == winner else [rng.choice(["unsupported_claim", "misses_required_fact", "wrong_action", "ignores_format"])])
            for key in ("candidate_1", "candidate_2", "candidate_3")
        }
        return {
            "id": f"rubric-{index:06d}",
            "source_facts": facts,
            "rubric": [
                "Use only the supplied facts.",
                "State the shipment status and promised date.",
                "Do not promise a refund unless refund_allowed is true.",
                "End with one concrete next action.",
            ],
            "winner": winner,
            "planned_defects": defects,
            "semantic_label": winner,
        }
    if family == "hard_v1_extra":
        scaffold = _policy_scaffold(index, seed, family)
        scaffold["surface_complexity"] = rng.choice(["nested exceptions", "cross references", "priority list", "definitions plus exceptions"])
        return scaffold
    raise ValueError(f"unknown LLM family: {family}")


SYSTEM_PROMPT = """You render training examples for a decision model. The program has already fixed every fact and label.
Do not solve, relabel, add exceptions, remove conditions, or change numeric values. Produce natural English surface text only.
Return one JSON object and no markdown."""


def render_prompt(family: str, scaffolds: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(list(scaffolds), ensure_ascii=False, indent=2)
    if family == "intent":
        task = "For each item, write one realistic user utterance expressing exactly the specified intent. Return fields id and utterance."
    elif family == "long_doc":
        task = (
            "For each item, write a long policy document containing every rule verbatim in meaning, plus realistic distractor sections, "
            "and a separate case narrative containing every case field. Return id, document, and case_text."
        )
    elif family == "rubric_judge":
        task = (
            "For each item, write three candidate responses. The designated winner must satisfy every rubric item; each other candidate "
            "must exhibit exactly its planned defects without introducing extra factual changes. Return id and candidates keyed candidate_1..3."
        )
    elif family == "hard_v1_extra":
        task = (
            "For each item, render the rules as a difficult but unambiguous policy with the requested surface complexity, and render the case "
            "as a separate narrative. Preserve rule priority, exception scope, all values, and the precomputed label. Return id, policy_text, case_text."
        )
    else:
        raise ValueError(f"unknown family: {family}")
    return f"{task}\nReturn {{\"items\": [...]}} with exactly one output per input id.\nINPUT:\n{payload}"


def _items_by_id(response: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    items = response.get("items")
    # Some OpenAI-compatible models unwrap a one-item batch despite being
    # asked for {"items": [...]}.  Accept the equivalent JSON shapes instead
    # of spending every retry on a purely structural mismatch.
    if isinstance(items, dict):
        items = list(items.values())
    if items is None and isinstance(response.get("item"), dict):
        items = [response["item"]]
    if items is None and isinstance(response.get("id"), str):
        items = [response]
    if not isinstance(items, list):
        raise ValueError("LLM response has no items list")
    result: Dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("LLM item has no string id")
        if item["id"] in result:
            raise ValueError(f"duplicate LLM item id: {item['id']}")
        result[item["id"]] = item
    return result


def materialize(family: str, scaffold: Mapping[str, Any], rendered: Mapping[str, Any], index: int, seed: int, model: str) -> Dict[str, Any]:
    if rendered.get("id") != scaffold.get("id"):
        raise ValueError("rendered id does not match scaffold")
    rng = stable_rng(seed, family, index)
    common_meta = {
        "llm_model": model,
        "label_source": "programmatic_scaffold",
        "scaffold": dict(scaffold),
    }
    if family == "intent":
        utterance = rendered.get("utterance")
        if not isinstance(utterance, str) or len(utterance.strip()) < 5:
            raise ValueError("intent utterance is missing or too short")
        values = list(INTENTS.items())
        options, value_to_key = shuffled_options(rng, values)
        return build_record(
            family, index, {"user_request": utterance.strip(), "context": scaffold["entities"]},
            "What is the user's primary intent?", options, value_to_key[scaffold["semantic_label"]],
            seed=seed, generator="program_scaffold_plus_llm_surface", extra_meta=common_meta,
        )
    if family in ("long_doc", "hard_v1_extra"):
        policy_key = "document" if family == "long_doc" else "policy_text"
        policy = rendered.get(policy_key)
        case_text = rendered.get("case_text")
        if not isinstance(policy, str) or not isinstance(case_text, str) or len(policy) < 200 or len(case_text) < 30:
            raise ValueError("policy/document or case text is missing or too short")
        if family == "long_doc" and len(policy.split()) < int(scaffold["target_words"] * 0.6):
            raise ValueError("long_doc render is substantially shorter than its target")
        values = [
            ("approve", "Approve"), ("deny", "Deny"),
            ("escalate", "Escalate for manual review"), ("insufficient", "Insufficient information"),
        ]
        options, value_to_key = shuffled_options(rng, values)
        state = {"policy": policy.strip(), "case": case_text.strip()}
        return build_record(
            family, index, state, "What is the correct decision under the policy?", options,
            value_to_key[scaffold["semantic_label"]], seed=seed,
            generator="program_solver_plus_llm_policy_render",
            dataset="hard-v1-extra-train" if family == "hard_v1_extra" else "synthetic-v1",
            extra_meta=common_meta,
        )
    if family == "rubric_judge":
        candidates = rendered.get("candidates")
        keys = ("candidate_1", "candidate_2", "candidate_3")
        if not isinstance(candidates, dict) or any(not isinstance(candidates.get(key), str) or len(candidates[key]) < 20 for key in keys):
            raise ValueError("rubric candidates are incomplete")
        order = list(keys)
        rng.shuffle(order)
        option_keys = [chr(ord("a") + i) for i in range(3)]
        options = {key: candidates[candidate] for key, candidate in zip(option_keys, order)}
        candidate_to_key = {candidate: key for key, candidate in zip(option_keys, order)}
        state = {"source_facts": scaffold["source_facts"], "rubric": scaffold["rubric"]}
        return build_record(
            family, index, state, "Which candidate best satisfies the rubric?", options,
            candidate_to_key[scaffold["semantic_label"]], seed=seed,
            generator="programmed_defects_plus_llm_candidate_render", extra_meta=common_meta,
        )
    raise ValueError(f"unknown family: {family}")


def verification_prompt(family: str, scaffolds: Sequence[Mapping[str, Any]], response: Mapping[str, Any]) -> str:
    return (
        "Audit the rendered items against their program scaffolds. Check that every numeric value, condition, exception scope, intent, "
        "planned defect, and designated winner is preserved. Do not judge style. Return "
        "{\"items\":[{\"id\":...,\"faithful\":true|false,\"issues\":[...]}]}.\n"
        f"FAMILY: {family}\nSCAFFOLDS:\n{json.dumps(list(scaffolds), ensure_ascii=False)}\n"
        f"RENDERED:\n{json.dumps(response, ensure_ascii=False)}"
    )


def faithful_ids(response: Mapping[str, Any]) -> Tuple[set, Dict[str, List[str]]]:
    accepted = set()
    issues: Dict[str, List[str]] = {}
    try:
        items = _items_by_id(response).values()
    except ValueError:
        items = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        if item.get("faithful") is True and not item.get("issues"):
            accepted.add(item["id"])
        else:
            raw = item.get("issues")
            issues[item["id"]] = [str(x) for x in raw] if isinstance(raw, list) else [str(raw or "failed verification")]
    return accepted, issues


def response_items(response: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return _items_by_id(response)

