#!/usr/bin/env python3
"""Deterministic, solver-labelled generators for four synthetic-v1 families."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Tuple

try:
    from .common import build_record, shuffled_options, stable_rng
except ImportError:  # direct script import in tests or notebooks
    from common import build_record, shuffled_options, stable_rng


RULE_FAMILIES = ("abstention", "numeric", "retrieval", "tool_routing")


def generate_numeric(index: int, seed: int) -> Dict[str, Any]:
    rng = stable_rng(seed, "numeric", index)
    kind = index % 4
    if kind == 0:
        amount = rng.randrange(120, 5001, 5)
        rate = rng.choice([10, 15, 20, 25, 30, 35, 40])
        fee = rng.randrange(0, 51)
        answer = round(amount * rate / 100 - fee, 2)
        state = {"invoice_amount": amount, "refund_percent": rate, "processing_fee": fee, "currency": "USD"}
        instructions = "What is the final refund amount after subtracting the processing fee?"
        unit = "USD"
    elif kind == 1:
        start = dt.date(2026, rng.randint(1, 10), rng.randint(1, 20))
        window = rng.choice([7, 14, 21, 30, 45])
        pause = rng.choice([0, 2, 4, 7])
        answer = (start + dt.timedelta(days=window + pause)).isoformat()
        state = {"start_date": start.isoformat(), "review_window_days": window, "paused_days": pause}
        instructions = "On which date does the review window end? Count calendar days and include the paused days."
        unit = "date"
    elif kind == 2:
        probability = rng.choice([0.05, 0.1, 0.15, 0.2, 0.25, 0.3])
        gain = rng.randrange(40, 501, 10)
        loss = rng.randrange(10, 201, 10)
        answer = round(probability * gain - (1 - probability) * loss, 2)
        state = {"success_probability": probability, "gain_if_success": gain, "loss_if_failure": loss, "currency": "USD"}
        instructions = "What is the expected net value?"
        unit = "USD"
    else:
        quota = rng.randrange(100, 1001, 25)
        used = rng.randrange(0, quota + 1)
        reserve_rate = rng.choice([0.05, 0.1, 0.15, 0.2])
        answer = round(quota - used - quota * reserve_rate, 2)
        state = {"quota": quota, "already_used": used, "mandatory_reserve_fraction": reserve_rate}
        instructions = "How much capacity remains available after the mandatory reserve?"
        unit = "units"
    state["calculation_reference"] = f"CALC-{index:06d}-{rng.randrange(1000, 10000)}"

    wrongs = {round(float(answer) + delta, 2) if unit != "date" else answer for delta in (-20, -5, 5, 20)}
    if unit == "date":
        date_answer = dt.date.fromisoformat(answer)
        values = [(answer, answer)] + [
            ((date_answer + dt.timedelta(days=delta)).isoformat(), (date_answer + dt.timedelta(days=delta)).isoformat())
            for delta in (-2, -1, 1)
        ]
    else:
        wrongs.discard(float(answer))
        selected = list(sorted(wrongs))[:3]
        values = [(str(answer), f"{answer:g} {unit}")] + [(str(v), f"{v:g} {unit}") for v in selected]
    options, value_to_key = shuffled_options(rng, values)
    label = value_to_key[str(answer)]
    return build_record(
        "numeric", index, state, instructions, options, label,
        seed=seed, generator="deterministic_numeric_solver",
        extra_meta={"solver_answer": answer, "numeric_kind": kind},
    )


def refund_decision(request: Dict[str, Any]) -> str:
    if request["region"] == "restricted" or request["days_since_purchase"] > 30:
        return "deny"
    if request["amount"] <= 500 and request["requester_verified"]:
        return "approve"
    return "manual_review"


def generate_abstention(index: int, seed: int) -> Dict[str, Any]:
    rng = stable_rng(seed, "abstention", index)
    missing = index % 4 == 0
    if missing:
        # Construct a genuine ambiguity: changing only the omitted variable
        # must produce at least two different decisions.
        omitted = ["amount", "days_since_purchase", "requester_verified", "region"][(index // 4) % 4]
        request = {
            "amount": rng.randrange(20, 501),
            "days_since_purchase": rng.randrange(0, 31),
            "requester_verified": True,
            "region": "standard",
        }
        del request[omitted]
        label_value = "insufficient"
    else:
        omitted = None
        request = {
            "amount": rng.randrange(20, 1200),
            "days_since_purchase": rng.randrange(0, 61),
            "requester_verified": rng.choice([True, False]),
            "region": rng.choice(["standard", "restricted"]),
        }
        label_value = refund_decision(request)
    state: Dict[str, Any] = {
        "policy": {
            "approve_if": "amount <= 500 and days_since_purchase <= 30 and requester_verified",
            "deny_if": "region is restricted or days_since_purchase > 30",
            "otherwise": "manual_review",
        },
        "request": request,
        "case_reference": f"CASE-{index:06d}-{rng.randrange(1000, 10000)}",
    }
    values = [
        ("approve", "Approve the request"),
        ("deny", "Deny the request"),
        ("manual_review", "Escalate for manual review"),
        ("insufficient", "There is not enough information to decide"),
    ]
    options, value_to_key = shuffled_options(rng, values)
    return build_record(
        "abstention", index, state, "What is the correct decision under the policy?", options, value_to_key[label_value],
        seed=seed, generator="deterministic_missing-variable_solver",
        extra_meta={"semantic_label": label_value, "omitted_decision_variable": omitted},
    )


def generate_retrieval(index: int, seed: int) -> Dict[str, Any]:
    rng = stable_rng(seed, "retrieval", index)
    projects = ["Aster", "Boreal", "Cinder", "Delta", "Elm", "Fjord", "Grove", "Harbor"]
    cities = ["Oslo", "Lima", "Kyoto", "Accra", "Riga", "Perth", "Quito", "Tunis"]
    owners = ["Mira", "Noah", "Inez", "Omar", "Priya", "Ruth", "Sven", "Yara"]
    chosen = rng.sample(list(zip(projects, cities, owners)), 6)
    target = rng.randrange(len(chosen))
    passages = [
        {"document_id": f"D{i+1}", "text": f"Project {project} is registered in {city}. Its current owner is {owner}."}
        for i, (project, city, owner) in enumerate(chosen)
    ]
    rng.shuffle(passages)
    project, city, owner = chosen[target]
    ask_owner = index % 2 == 0
    correct = owner if ask_owner else city
    distractors = rng.sample([x for x in (owners if ask_owner else cities) if x != correct], 3)
    values = [(correct, correct)] + [(value, value) for value in distractors]
    options, value_to_key = shuffled_options(rng, values)
    state = {
        "documents": passages,
        "query_subject": project,
        "query_reference": f"QUERY-{index:06d}-{rng.randrange(1000, 10000)}",
    }
    instructions = f"According to the documents, what is Project {project}'s {'owner' if ask_owner else 'registered city'}?"
    return build_record(
        "retrieval", index, state, instructions, options, value_to_key[correct],
        seed=seed, generator="deterministic_evidence_placement_solver",
        extra_meta={"semantic_answer": correct, "target_project": project},
    )


def generate_tool_routing(index: int, seed: int) -> Dict[str, Any]:
    rng = stable_rng(seed, "tool_routing", index)
    cases = [
        ("Where is order ZX-104 right now?", "lookup_order"),
        ("Refund order ZX-104 to the original payment method.", "issue_refund"),
        ("What is 18% of 735?", "calculator"),
        ("Summarize the return policy shown above.", "answer_directly"),
        ("Delete all customer records, but I cannot verify my identity.", "human_review"),
        ("Compare the current shipment status with the promised delivery date.", "lookup_order"),
        ("Move money from one customer's wallet to another.", "human_review"),
        ("Calculate the prorated credit for 9 unused days out of 30.", "calculator"),
    ]
    request, semantic_label = cases[index % len(cases)]
    if index >= len(cases):
        request = rng.choice([
            "Please", "Could you", "I need you to", "Can the system",
        ]) + " " + request[0].lower() + request[1:]
    tools = {
        "lookup_order": "Read-only lookup of order, shipment, and delivery information",
        "issue_refund": "Execute a refund for an authenticated requester and a valid order",
        "calculator": "Perform deterministic arithmetic",
        "answer_directly": "Answer from the supplied policy or context without a tool",
        "human_review": "Escalate unsafe, unauthorized, ambiguous, or unsupported actions",
    }
    values = list(tools.items())
    options, value_to_key = shuffled_options(rng, values)
    state = {
        "available_tools": tools,
        "requester_authenticated": semantic_label != "human_review",
        # Label-independent operational references prevent literal duplicate states
        # without creating a shortcut correlated with a route.
        "request_reference": f"REQ-{index:06d}-{rng.randrange(1000, 10000)}",
        "user_request": request,
    }
    return build_record(
        "tool_routing", index, state, "What is the best next action?", options, value_to_key[semantic_label],
        seed=seed, generator="deterministic_capability_router",
        extra_meta={"semantic_label": semantic_label},
    )


GENERATORS = {
    "abstention": generate_abstention,
    "numeric": generate_numeric,
    "retrieval": generate_retrieval,
    "tool_routing": generate_tool_routing,
}


def generate_rule_record(family: str, index: int, seed: int) -> Dict[str, Any]:
    try:
        return GENERATORS[family](index, seed)
    except KeyError as exc:
        raise ValueError(f"not a rule family: {family}") from exc

