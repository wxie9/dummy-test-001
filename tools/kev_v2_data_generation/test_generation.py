#!/usr/bin/env python3
"""Standard-library smoke tests; no API calls."""

from __future__ import annotations

import unittest

from common import validate_record
from llm_generators import faithful_ids, make_scaffold, materialize, response_items
from rule_generators import RULE_FAMILIES, generate_rule_record, refund_decision


class RuleGenerationTest(unittest.TestCase):
    def test_rule_families_are_valid_and_unique(self) -> None:
        for family in RULE_FAMILIES:
            rows = [generate_rule_record(family, index, 123) for index in range(30)]
            self.assertTrue(all(not validate_record(row) for row in rows), family)
            self.assertEqual(len(rows), len({row["_meta"]["state_sha256"] for row in rows}), family)

    def test_abstention_missing_fields_are_decision_critical(self) -> None:
        domains = {
            "amount": [20, 900],
            "days_since_purchase": [5, 50],
            "requester_verified": [True, False],
            "region": ["standard", "restricted"],
        }
        for index in range(0, 64, 4):
            row = generate_rule_record("abstention", index, 123)
            omitted = row["_meta"]["omitted_decision_variable"]
            partial = row["state"]["request"]
            outcomes = set()
            for value in domains[omitted]:
                completed = dict(partial)
                completed[omitted] = value
                outcomes.add(refund_decision(completed))
            self.assertGreaterEqual(len(outcomes), 2, (index, omitted, outcomes))

    def test_tool_routes_do_not_execute_privileged_actions_unauthenticated(self) -> None:
        for index in range(80):
            row = generate_rule_record("tool_routing", index, 123)
            semantic = row["_meta"]["semantic_label"]
            if semantic != "human_review":
                self.assertTrue(row["state"]["requester_authenticated"])

    def test_llm_materialization_shapes(self) -> None:
        rendered = {
            "intent": lambda s: {"id": s["id"], "utterance": "Please cancel the subscription attached to my account."},
            "long_doc": lambda s: {"id": s["id"], "document": "Policy clause. " * s["target_words"], "case_text": "The request contains every required case field and value."},
            "hard_v1_extra": lambda s: {"id": s["id"], "policy_text": "Policy. " * 80, "case_text": "The request contains every required case field and value."},
            "rubric_judge": lambda s: {
                "id": s["id"],
                "candidates": {
                    "candidate_1": "A detailed response with status, date, evidence limits, and a next action.",
                    "candidate_2": "A different response that intentionally omits a required fact from the rubric.",
                    "candidate_3": "A different response that includes an unsupported claim and an action.",
                },
            },
        }
        for family, maker in rendered.items():
            scaffold = make_scaffold(family, 0, 123)
            row = materialize(family, scaffold, maker(scaffold), 0, 123, "deepseek-v4-flash")
            self.assertFalse(validate_record(row), family)

    def test_single_item_responses_may_be_unwrapped(self) -> None:
        rendered = {"id": "long_doc-000001", "document": "Policy", "case_text": "Case"}
        self.assertEqual(response_items(rendered)[rendered["id"]], rendered)
        accepted, issues = faithful_ids({"id": rendered["id"], "faithful": True, "issues": []})
        self.assertEqual(accepted, {rendered["id"]})
        self.assertEqual(issues, {})

    def test_rubric_scaffolds_have_enough_unique_states_for_target(self) -> None:
        scaffolds = [make_scaffold("rubric_judge", index, 20261104) for index in range(7288)]
        encoded = {
            repr(sorted(scaffold["source_facts"].items()))
            for scaffold in scaffolds
        }
        self.assertEqual(len(encoded), 7288)


if __name__ == "__main__":
    unittest.main()

