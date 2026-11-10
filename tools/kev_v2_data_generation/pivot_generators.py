#!/usr/bin/env python3
"""Deterministic structured-world generators for the 45 DecisionPivot categories.

The output is deliberately not natural-language training data.  Each scaffold
contains a machine-readable world, a solver trace, semantic answer choices, and
one gold value.  A later rendering stage may turn it into prose, but may not
change these semantics.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

try:
    from .common import canonical_json, stable_rng
    from .pivot_spec import CATEGORY_BY_ID, CategorySpec
except ImportError:
    from common import canonical_json, stable_rng
    from pivot_spec import CATEGORY_BY_ID, CategorySpec


Json = Dict[str, Any]


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _options(answer: Any, distractors: Iterable[Any]) -> List[Any]:
    result = [answer]
    for item in distractors:
        if item != answer and item not in result:
            result.append(item)
    if len(result) < 3:
        raise ValueError(f"not enough distinct options for {answer!r}: {result!r}")
    return result[:4]


def _finalize(
    spec: CategorySpec,
    index: int,
    seed: int,
    state: Json,
    answer: Any,
    distractors: Iterable[Any],
    solver: str,
    trace: Sequence[str],
    question_intent: str,
) -> Json:
    values = _options(answer, distractors)
    rng = stable_rng(seed, spec.category_id, index, attempt=991)
    rng.shuffle(values)
    option_map = {chr(ord("a") + pos): value for pos, value in enumerate(values)}
    label = next(key for key, value in option_map.items() if value == answer)
    semantic = {
        "state": state,
        "question_intent": question_intent,
        "options": option_map,
        "answer_value": answer,
    }
    state_hash = _sha(semantic)
    return {
        "id": f"kev-pivot-augmentation-v1/{spec.category_id}/{index:06d}",
        "family": spec.family,
        "category_id": spec.category_id,
        "category_zh": spec.name_zh,
        "difficulty": spec.difficulty,
        "state": state,
        "question_spec": {
            "intent": question_intent,
            "semantic_options": option_map,
            "label": label,
            "answer_value": answer,
        },
        "solver": {"name": solver, "trace": list(trace), "answer": answer},
        "_meta": {
            "seed": seed,
            "index": index,
            "state_sha256": state_hash,
            "generator_version": "pivot-structured-v1",
            "provenance": "independent_targeted_generation_not_decisionpivot_rows",
            "split": "train",
        },
    }


def _answerable_facts(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    if spec.category_id == "facts_multitable_subtraction":
        left = [rng.randint(20, 180) for _ in range(rng.randint(3, 5))]
        right = [rng.randint(10, 120) for _ in range(rng.randint(2, 4))]
        answer = sum(left) - sum(right)
        state = {"table_a": left, "table_b": right, "operation": "sum(table_a)-sum(table_b)"}
        return state, answer, [sum(left), sum(right), answer + rng.choice([-2, -1, 1, 2])], "multi_table_arithmetic", [f"sum_a={sum(left)}", f"sum_b={sum(right)}", f"difference={answer}"], "Compute the requested aggregate difference across both tables."

    depth = 4 if spec.category_id == "facts_four_hop" else 2
    if spec.category_id == "facts_inheritance_reasoning":
        depth = 3
    nodes = [f"entity_{index}_{i}" for i in range(depth + 1)]
    colors = ["amber", "blue", "copper", "green", "ivory", "violet"]
    terminal_value = rng.choice(colors)
    edges = [{"from": nodes[i], "relation": "inherits_from", "to": nodes[i + 1]} for i in range(depth)]
    state = {
        "relations": edges,
        "attributes": {nodes[-1]: {"classification": terminal_value}},
        "query_entity": nodes[0],
        "inherit_attribute": "classification",
    }
    distractors = rng.sample([value for value in colors if value != terminal_value], 3)
    return state, terminal_value, distractors, "graph_attribute_inheritance", [*(f"{e['from']}->{e['to']}" for e in edges), f"terminal={terminal_value}"], "Follow the inheritance chain and identify the inherited classification."


def _permission(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    actions = ["read", "write", "export", "delete"]
    action = rng.choice(actions)
    depth = 3 if spec.category_id in {"permission_three_level_tree", "permission_level3"} else 2
    chain = [f"role_{index}_{i}" for i in range(depth)]
    resource = f"resource_{rng.randrange(1000, 9999)}"
    scope = rng.choice(["project", "folder", "record"])
    sealed = spec.category_id == "permission_sealed_resource" and index % 2 == 0
    explicit_deny = index % 3 == 0
    grant_action = action
    query_action = action
    if spec.category_id == "permission_action_change":
        query_action = rng.choice([candidate for candidate in actions if candidate != grant_action]) if index % 2 else grant_action
    scope_match = not (spec.category_id == "permission_scope_change" and index % 2)
    state = {
        "user": f"user_{index}",
        "role_chain": chain,
        "inherits": [{"child": chain[i], "parent": chain[i + 1]} for i in range(len(chain) - 1)],
        "grant": {"role": chain[-1], "action": grant_action, "scope": scope},
        "deny": {"role": chain[0], "action": query_action, "active": explicit_deny},
        "resource": {"id": resource, "scope": scope if scope_match else "other_scope", "sealed": sealed},
        "query": {"action": query_action, "resource": resource},
        "policy": {"explicit_deny_overrides": True, "sealed_resources_deny_all": True},
    }
    allowed = not sealed and not explicit_deny and query_action == grant_action and scope_match
    answer = "allow" if allowed else "deny"
    reasons = [f"sealed={sealed}", f"explicit_deny={explicit_deny}", f"action_match={query_action == grant_action}", f"scope_match={scope_match}"]
    return state, answer, ["deny" if allowed else "allow", "manual_review"], "permission_graph_solver", reasons, "Determine whether the requested action is permitted after inheritance and overrides."


def _policy(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    amount = 20 + index
    verified = rng.choice([True, False])
    legal_hold = rng.choice([True, False])
    exports = rng.randint(0, 6)
    privileged = rng.choice([True, False])
    case = {"amount": amount, "verified": verified, "legal_hold": legal_hold, "exports_30d": exports, "privileged": privileged}
    rules = [
        {"priority": 100, "if": "legal_hold and amount>=100", "then": "escalate"},
        {"priority": 90, "if": "not verified and exports_30d>=3", "then": "deny"},
        {"priority": 80, "if": "privileged and amount<500", "then": "approve"},
        {"priority": 10, "if": "amount<200 and exports_30d<2", "then": "approve"},
    ]
    exceptions = [
        {"for": "legal_hold", "if": "amount<100", "effect": "skip_rule"},
        {"for": "unverified", "if": "privileged", "effect": "skip_rule"},
        {"for": "privileged", "if": "legal_hold", "effect": "skip_rule"},
        {"for": "small_request", "if": "exports_30d>=2", "effect": "skip_rule"},
    ]
    if spec.category_id == "policy_rule_precedence":
        exceptions = exceptions[:1]
    elif spec.category_id == "policy_exception_handling":
        exceptions = exceptions[:2]
    if legal_hold and amount >= 100:
        answer, decisive = "escalate", "legal_hold"
    elif not verified and exports >= 3 and not privileged:
        answer, decisive = "deny", "unverified_high_exports"
    elif privileged and amount < 500 and not legal_hold:
        answer, decisive = "approve", "privileged_small"
    elif amount < 200 and exports < 2:
        answer, decisive = "approve", "small_request"
    else:
        answer, decisive = "escalate", "default"
    state = {"ordered_rules": rules, "exceptions": exceptions, "case": case, "default": "escalate"}
    return state, answer, [x for x in ["approve", "deny", "escalate"] if x != answer], "ordered_policy_solver", [f"decisive={decisive}"], "Apply the ordered policy and its exceptions to choose the final decision."


def _log_count(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    start = rng.randint(100, 300)
    end = start + rng.randint(20, 80)
    start_inclusive = rng.choice([True, False])
    end_inclusive = rng.choice([True, False])
    wanted_type, wanted_status = "export", "success"
    events = []
    forced_times = [start, end, start + 1, end - 1]
    for event_id in range(rng.randint(9, 15)):
        timestamp = forced_times[event_id] if event_id < len(forced_times) else rng.randint(start - 15, end + 15)
        events.append({
            "id": f"evt_{index}_{event_id}",
            "minute": timestamp,
            "type": rng.choice(["export", "login", "update"]),
            "status": rng.choice(["success", "failed"]),
        })
    events[0].update(type=wanted_type, status=wanted_status)
    events[1].update(type=wanted_type, status=wanted_status)

    def in_window(minute: int) -> bool:
        left = minute >= start if start_inclusive else minute > start
        right = minute <= end if end_inclusive else minute < end
        return left and right

    matching = [event for event in events if event["type"] == wanted_type and event["status"] == wanted_status and in_window(event["minute"])]
    answer = len(matching)
    without_status = sum(event["type"] == wanted_type and in_window(event["minute"]) for event in events)
    both_inclusive = sum(event["type"] == wanted_type and event["status"] == wanted_status and start <= event["minute"] <= end for event in events)
    state = {
        "window": {"start_minute": start, "end_minute": end, "start_inclusive": start_inclusive, "end_inclusive": end_inclusive},
        "filter": {"type": wanted_type, "status": wanted_status},
        "events": events,
    }
    return state, answer, [answer - 1, answer + 1, without_status, both_inclusive], "event_window_counter", [f"matching_ids={[e['id'] for e in matching]}", f"count={answer}"], "Count exactly the events that satisfy the filter and time-window semantics."


def _schedule(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    # Mixed-radix request fields provide at least 720 genuinely different
    # scheduling worlds before any random equipment variation is considered.
    start = 8 + index % 12
    duration = 1 + (index // 12) % 3
    attendees = 3 + (index // 36) % 20
    existing = {"start": start + rng.choice([-1, 0, 1]), "end": start + rng.choice([1, 2, 3])}
    if existing["end"] <= existing["start"]:
        existing["end"] = existing["start"] + 1
    requested = {"start": start, "end": start + duration, "attendees": attendees, "equipment": rng.choice(["projector", "lab_kit", "none"])}
    room = {"capacity": rng.randint(6, 20), "equipment": rng.sample(["projector", "lab_kit"], rng.randint(0, 2))}
    overlap = max(requested["start"], existing["start"]) < min(requested["end"], existing["end"])
    capacity_ok = requested["attendees"] <= room["capacity"]
    equipment_ok = requested["equipment"] == "none" or requested["equipment"] in room["equipment"]
    if spec.category_id == "schedule_equipment":
        overlap = False
        capacity_ok = True
        if index % 2 == 0:
            equipment_ok = False
        else:
            equipment_ok = True
    elif spec.category_id == "schedule_capacity":
        overlap = False
        equipment_ok = True
        capacity_ok = index % 2 == 1
    elif spec.category_id == "schedule_level3":
        # Balanced controls: odd rows satisfy all constraints; even rows fail
        # exactly one of the three, rotated by index.
        if index % 2:
            overlap = False
            capacity_ok = True
            equipment_ok = True
        else:
            failed = (index // 2) % 3
            overlap = failed == 0
            capacity_ok = failed != 1
            equipment_ok = failed != 2
    # Synchronize the serialized world with the deliberately controlled truth
    # values above, so the solver trace can be recomputed from state alone.
    if overlap:
        existing = {"start": requested["start"], "end": requested["end"]}
    else:
        existing = {"start": requested["end"] + 1, "end": requested["end"] + 2}
    room["capacity"] = requested["attendees"] if capacity_ok else max(0, requested["attendees"] - 1)
    if requested["equipment"] == "none":
        requested["equipment"] = "projector"
    if equipment_ok:
        if requested["equipment"] not in room["equipment"]:
            room["equipment"].append(requested["equipment"])
    else:
        room["equipment"] = [item for item in room["equipment"] if item != requested["equipment"]]
    feasible = not overlap and capacity_ok and equipment_ok
    state = {"requested": requested, "existing_booking": existing, "room": room, "constraints": ["no_overlap", "capacity", "equipment"]}
    answer = "feasible" if feasible else "conflict"
    focus = {
        "schedule_equipment": "the required equipment condition",
        "schedule_capacity": "the room-capacity condition",
        "schedule_level3": "the combined time, capacity, and equipment conditions",
    }[spec.category_id]
    intent = f"Determine whether the requested booking is feasible, with particular attention to {focus}."
    return state, answer, ["conflict" if feasible else "feasible", "insufficient"], "schedule_constraint_solver", [f"overlap={overlap}", f"capacity_ok={capacity_ok}", f"equipment_ok={equipment_ok}"], intent


def _state_goal(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    object_a, object_b = f"account_{index}_a", f"account_{index}_b"
    initial = {object_a: {"status": "draft", "count": rng.randint(1, 5), "owner": "team_a"}, object_b: {"status": "draft", "count": 0, "owner": "team_b"}}
    steps = [
        {"op": "increment", "object": object_a, "amount": 2},
        {"op": "set_status", "object": object_a, "value": "approved"},
        {"op": "set_owner", "object": object_a, "value": "team_b"},
    ]
    inject_failure = index % 2 == 0
    if spec.category_id == "state_missing_step" and inject_failure:
        steps.pop(1)
    if spec.category_id == "state_wrong_object" and inject_failure:
        steps[1]["object"] = object_b
    if spec.category_id == "state_step_order" and inject_failure:
        steps[0], steps[1] = steps[1], steps[0]
    final = json.loads(json.dumps(initial))
    for step in steps:
        obj = final[step["object"]]
        if step["op"] == "increment":
            obj["count"] += step["amount"]
        elif step["op"] == "set_status":
            obj["status"] = step["value"]
        else:
            obj["owner"] = step["value"]
    goal = {"object": object_a, "status": "approved", "owner": "team_b", "count": initial[object_a]["count"] + 2}
    if spec.category_id == "state_equality_failure" and inject_failure:
        goal["owner"] = "team_c"
    if spec.category_id == "state_quantity_failure" and inject_failure:
        goal["count"] += 1
    if spec.category_id == "state_content_failure" and inject_failure:
        goal["status"] = "published"
    observed = final[goal["object"]]
    achieved = all(observed[key] == value for key, value in goal.items() if key != "object")
    answer = "achieved" if achieved else "not_achieved"
    # final is solver-private; exposing it would let the renderer state the
    # answer instead of requiring the model to execute the transitions.
    state = {"initial": initial, "steps": steps, "goal": goal}
    mismatches = [key for key, value in goal.items() if key != "object" and observed[key] != value]
    focus = {
        "state_equality_failure": "exact equality of all required fields",
        "state_missing_step": "completion of every required transition",
        "state_wrong_object": "whether operations affected the intended object",
        "state_step_order": "the effect of the operation order",
        "state_quantity_failure": "the numeric target condition",
        "state_content_failure": "the required content value",
    }[spec.category_id]
    intent = f"Execute the operations and assess {focus} to decide whether the goal is achieved."
    return state, answer, ["not_achieved" if achieved else "achieved", "insufficient"], "state_transition_simulator", [f"mismatches={mismatches}"], intent


def _triage(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    categories = {"security": 0, "safety": 1, "billing": 2, "general": 3}
    items = []
    for pos in range(4):
        category = rng.choice(list(categories))
        items.append({"id": f"ticket_{index}_{pos}", "category": category, "severity": rng.randint(1, 5), "age_minutes": rng.randint(1, 240)})
    ordered = sorted(items, key=lambda x: (categories[x["category"]], -x["severity"], -x["age_minutes"], x["id"]))
    answer = ordered[0]["id"]
    state = {"priority_order": list(categories), "tie_breakers": ["higher_severity", "older_first"], "tickets": items}
    return state, answer, [item["id"] for item in items if item["id"] != answer], "lexicographic_triage_sort", [f"ordered={[x['id'] for x in ordered]}"], "Select the ticket that must be handled first under the triage policy."


def _clause_change(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    region = rng.choice(["north", "south", "east"])
    amount = 50 + index % 751
    level = 1 + (index // 751) % 4
    old_minimum = 150 + index * 2
    old = {"region": "north", "min_amount": old_minimum, "max_level": 3, "decision": "approve"}
    new = dict(old)
    if spec.category_id == "clause_outside_condition":
        new["min_amount"] = old_minimum + 100
        region = "south" if index % 2 == 0 else "north"
        if index % 2:
            amount = old_minimum + 50
    else:
        new["min_amount"] = old_minimum + 150
        new["max_level"] = 2
        region = "north"
        level = 1
        amount = old_minimum + (50 if index % 2 == 0 else 200)
    case = {"region": region, "amount": amount, "level": level}
    def applies(rule: Mapping[str, Any]) -> bool:
        return case["region"] == rule["region"] and case["amount"] >= rule["min_amount"] and case["level"] <= rule["max_level"]
    old_decision = "approve" if applies(old) else "review"
    new_decision = "approve" if applies(new) else "review"
    answer = "changed" if old_decision != new_decision else "unchanged"
    # The paired decisions are solver outputs and must not enter the prompt.
    state = {"old_clause": old, "new_clause": new, "case": case}
    return state, answer, ["unchanged" if answer == "changed" else "changed", "insufficient"], "paired_clause_evaluator", [f"old={old_decision}", f"new={new_decision}"], "Determine whether the clause modification changes the outcome for this case."


def _allowed_versions(domain: Sequence[int], constraints: Sequence[Mapping[str, Any]]) -> List[int]:
    result = []
    for version in domain:
        ok = True
        for constraint in constraints:
            op, bound = constraint["op"], constraint["version"]
            ok &= {">=": version >= bound, ">": version > bound, "<=": version <= bound, "<": version < bound, "==": version == bound}[op]
        if ok:
            result.append(version)
    return result


def _dependency(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    domain = list(range(1, 8))
    constraints: List[Json]
    graph: List[Json] = []
    installed = [f"pkg_{index}_{i}" for i in range(5)]
    if spec.category_id == "dependency_version_conflict":
        pivot = rng.randint(2, 6)
        constraints = [{"op": ">=", "version": pivot}, {"op": "<" if index % 2 == 0 else "<=", "version": pivot}]
    elif spec.category_id == "dependency_exclusive_boundary":
        low = rng.randint(1, 4)
        constraints = [{"op": ">", "version": low}, {"op": "<", "version": low + (1 if index % 2 == 0 else 2)}]
    elif spec.category_id == "dependency_ordinary_boundary":
        low = rng.randint(1, 4)
        constraints = [{"op": ">=", "version": low}, {"op": "<=", "version": low - 1 if index % 2 == 0 else low + 2}]
    elif spec.category_id == "dependency_self_constraint":
        current = rng.randint(2, 6)
        constraints = [{"op": "==", "version": current}, {"op": ">=", "version": current + 1 if index % 2 == 0 else current - 1}]
    else:
        constraints = [{"op": ">=", "version": rng.randint(1, 3)}, {"op": "<=", "version": rng.randint(4, 7)}]
    allowed = _allowed_versions(domain, constraints)
    if spec.category_id in {"dependency_complex_closure", "dependency_missing_item", "dependency_runtime"}:
        edge_type = "runtime" if spec.category_id == "dependency_runtime" else "required"
        depth = 4 if spec.category_id == "dependency_complex_closure" else 2
        graph = [{"from": installed[i], "to": installed[i + 1], "type": edge_type if i == depth - 1 else "required"} for i in range(depth)]
        if spec.category_id == "dependency_missing_item":
            if index % 2 == 0:
                installed.remove(graph[-1]["to"])
        elif spec.category_id in {"dependency_complex_closure", "dependency_runtime"} and index % 2 == 0:
            installed.remove(graph[-1]["to"])
        required_nodes = {edge["to"] for edge in graph if edge["type"] in {"required", "runtime"}}
        graph_ok = required_nodes.issubset(installed)
    else:
        graph_ok = True
    satisfiable = bool(allowed) and graph_ok
    answer = "resolvable" if satisfiable else "conflict"
    state = {"version_domain": domain, "root_constraints": constraints, "dependency_graph": graph, "installed_packages": installed}
    return state, answer, ["conflict" if satisfiable else "resolvable", "insufficient"], "dependency_constraint_solver", [f"allowed_versions={allowed}", f"graph_ok={graph_ok}"], "Determine whether all version and dependency constraints can be satisfied."


def _ledger(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    base = dt.date(2026, rng.randint(1, 10), rng.randint(1, 20))
    entries = []
    for pos in range(rng.randint(4, 7)):
        amount = rng.randint(20, 250)
        fee_rate = rng.choice([0.0, 0.02, 0.05, 0.1])
        entries.append({"id": f"line_{index}_{pos}", "date": (base + dt.timedelta(days=pos)).isoformat(), "amount": amount, "fee_rate": fee_rate})
    expected = round(sum(e["amount"] * (1 + e["fee_rate"]) for e in entries), 2)
    claimed = expected
    included_ids = [e["id"] for e in entries]
    valid_start, valid_end = base, base + dt.timedelta(days=len(entries) - 1)
    inject_failure = index % 2 == 0
    if spec.category_id == "ledger_batch_total_error" and inject_failure:
        claimed = round(expected + rng.choice([-7, -3, 4, 9]), 2)
    elif spec.category_id == "ledger_missing_entry" and inject_failure:
        included_ids.pop(rng.randrange(len(included_ids)))
    elif spec.category_id == "ledger_fee_error" and inject_failure:
        claimed = round(sum(e["amount"] for e in entries), 2)
    elif spec.category_id == "ledger_date_error" and inject_failure:
        entries[-1]["date"] = (valid_end + dt.timedelta(days=2)).isoformat()
    included_total = round(sum(e["amount"] * (1 + e["fee_rate"]) for e in entries if e["id"] in included_ids), 2)
    dates_ok = all(valid_start <= dt.date.fromisoformat(e["date"]) <= valid_end for e in entries)
    complete = len(included_ids) == len(entries)
    correct_total = claimed == expected
    valid = dates_ok and complete and correct_total
    answer = "valid" if valid else "invalid"
    # expected_total remains in the solver trace only; the learner must
    # recompute it from entries and fee rates.
    state = {"entries": entries, "batch": {"included_ids": included_ids, "claimed_total": claimed, "valid_start": valid_start.isoformat(), "valid_end": valid_end.isoformat()}}
    return state, answer, ["invalid" if valid else "valid", "insufficient"], "ledger_reconciliation_solver", [f"expected={expected}", f"included_total={included_total}", f"complete={complete}", f"dates_ok={dates_ok}"], "Reconcile the ledger and determine whether the submitted batch is valid."


def _record_rule(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    # Mixed-radix coverage avoids birthday collisions at the 500+ row target
    # while changing the actual arithmetic world, not merely an identifier.
    quantity = 2 + index % 29
    unit_price = 5 + (index // 29) % 79
    tax_rate = [0.05, 0.1, 0.15, 0.2][(index // (29 * 79)) % 4]
    subtotal = quantity * unit_price
    total = round(subtotal * (1 + tax_rate), 2)
    record = {"quantity": quantity, "unit_price": unit_price, "tax_rate": tax_rate, "subtotal": subtotal, "total": total, "scope": "order"}
    if spec.category_id == "record_derived_field" and index % 2 == 0:
        record["total"] = round(total + rng.choice([-2, 2, 5]), 2)
    if spec.category_id == "record_field_scope" and index % 2 == 0:
        record["scope"] = "line_item"
    rule = {"subtotal": "quantity*unit_price", "total": "subtotal*(1+tax_rate)", "required_scope": "order"}
    if spec.category_id == "record_field_scope":
        rule["field_dependencies"] = {
            "subtotal": ["line_item.quantity", "line_item.unit_price"],
            "total": ["order.subtotal", "order.tax_rate"],
        }
        rule["validation_focus"] = "cross_scope_field_dependency"
    else:
        rule["validation_focus"] = "derived_field_arithmetic"
    valid = record["subtotal"] == subtotal and record["total"] == total and record["scope"] == rule["required_scope"]
    answer = "valid" if valid else "invalid"
    return {"record": record, "rule": rule}, answer, ["invalid" if valid else "valid", "insufficient"], "record_constraint_solver", [f"expected_subtotal={subtotal}", f"expected_total={total}", f"scope_ok={record['scope'] == 'order'}"], "Validate the record against its derived-field and scope rules."


def _filter_match(spec: CategorySpec, index: int, seed: int) -> Tuple[Json, Any, List[Any], str, List[str], str]:
    rng = stable_rng(seed, spec.category_id, index)
    candidates = []
    certs = ["A", "B", "C", "D"]
    for pos in range(4):
        candidates.append({
            "id": f"candidate_{index}_{pos}",
            "certificates": rng.sample(certs, rng.randint(1, 4)),
            "region": rng.choice(["domestic", "foreign"]),
            "insured": rng.choice([True, False]),
            "capacity_value": rng.randint(400, 2400),
            "capacity_unit": rng.choice(["kg", "lb"]),
        })
    if spec.category_id == "filter_k_of_n":
        k = 3
        scores = [(c["id"], sum(cert in c["certificates"] for cert in certs)) for c in candidates]
        best = max(scores, key=lambda item: (item[1], item[0]))
        answer = best[0]
        requirements = {"kind": "k_of_n", "k": k, "certificates": certs, "tie_breaker": "higher_id"}
        trace = [f"scores={scores}"]
    elif spec.category_id == "filter_conditional_rule":
        eligible = [c for c in candidates if c["region"] == "domestic" or c["insured"]]
        if not eligible:
            candidates[0]["insured"] = True
            eligible = [candidates[0]]
        answer = max(eligible, key=lambda c: (len(c["certificates"]), c["id"]))["id"]
        requirements = {"kind": "conditional", "rule": "foreign requires insured", "tie_breaker": "most_certificates_then_higher_id"}
        trace = [f"eligible={[c['id'] for c in eligible]}"]
    else:
        def kg(candidate: Mapping[str, Any]) -> float:
            return candidate["capacity_value"] if candidate["capacity_unit"] == "kg" else candidate["capacity_value"] * 0.45359237
        answer = max(candidates, key=lambda c: (kg(c), c["id"]))["id"]
        requirements = {"kind": "converted_minimum", "conversion": "1 lb = 0.45359237 kg", "choose": "largest_capacity_kg"}
        trace = [f"kg_values={[(c['id'], round(kg(c), 3)) for c in candidates]}"]
    return {"candidates": candidates, "requirements": requirements}, answer, [c["id"] for c in candidates if c["id"] != answer], "constraint_filter_solver", trace, "Select the candidate that best satisfies the stated filtering rule."


GENERATORS: Dict[str, Callable[[CategorySpec, int, int], Tuple[Json, Any, List[Any], str, List[str], str]]] = {
    "answerable_facts": _answerable_facts,
    "permission_inheritance": _permission,
    "policy_case": _policy,
    "log_count_check": _log_count,
    "schedule_conflict": _schedule,
    "state_goal": _state_goal,
    "triage_order": _triage,
    "clause_change": _clause_change,
    "dependency_resolution": _dependency,
    "ledger_reconcile": _ledger,
    "record_rule": _record_rule,
    "filter_match": _filter_match,
}


def validate_structured(scaffold: Mapping[str, Any]) -> List[str]:
    problems: List[str] = []
    category_id = scaffold.get("category_id")
    if category_id not in CATEGORY_BY_ID:
        problems.append("unknown category_id")
    question = scaffold.get("question_spec")
    if not isinstance(question, Mapping):
        problems.append("missing question_spec")
    else:
        options = question.get("semantic_options")
        if not isinstance(options, Mapping) or len(options) < 3:
            problems.append("semantic_options must contain at least three choices")
        elif question.get("label") not in options:
            problems.append("label is not an option key")
        elif options[question["label"]] != question.get("answer_value"):
            problems.append("label does not point to answer_value")
    solver = scaffold.get("solver")
    if not isinstance(solver, Mapping) or solver.get("answer") != question.get("answer_value") if isinstance(question, Mapping) else True:
        problems.append("solver answer mismatch")
    meta = scaffold.get("_meta")
    if not isinstance(meta, Mapping) or not meta.get("state_sha256"):
        problems.append("missing state hash")
    return problems


def generate_structured(category_id: str, index: int, seed: int = 20261106) -> Json:
    try:
        spec = CATEGORY_BY_ID[category_id]
    except KeyError as exc:
        raise ValueError(f"unknown DecisionPivot category: {category_id}") from exc
    generator = GENERATORS[spec.family]
    state, answer, distractors, solver, trace, intent = generator(spec, index, seed)
    scaffold = _finalize(spec, index, seed, state, answer, distractors, solver, trace, intent)
    problems = validate_structured(scaffold)
    if problems:
        raise ValueError(f"invalid scaffold {scaffold['id']}: {'; '.join(problems)}")
    return scaffold
