#!/usr/bin/env python3
"""Standard-library tests for Pivot structured generation; no API calls."""

from __future__ import annotations

import unittest

from pivot_generators import generate_structured, validate_structured
from pivot_llm_renderer import local_render_problems, materialize, parse_audit, parse_items
from pivot_spec import CATEGORIES, TARGETS, total_target


class PivotSpecificationTest(unittest.TestCase):
    def test_exact_allocation(self) -> None:
        self.assertEqual(len(CATEGORIES), 45)
        self.assertEqual(total_target(), 20_000)
        self.assertEqual(sum(TARGETS.values()), 20_000)

    def test_every_family_has_valid_deterministic_scaffolds(self) -> None:
        hashes = set()
        for spec in CATEGORIES:
            for index in range(12):
                row = generate_structured(spec.category_id, index, 20261106)
                self.assertFalse(validate_structured(row), (spec.category_id, index))
                self.assertEqual(row, generate_structured(spec.category_id, index, 20261106))
                state_hash = row["_meta"]["state_sha256"]
                self.assertNotIn(state_hash, hashes, (spec.category_id, index))
                hashes.add(state_hash)

    def test_labels_point_to_solver_answers(self) -> None:
        for spec in CATEGORIES:
            row = generate_structured(spec.category_id, 19, 7)
            question = row["question_spec"]
            self.assertEqual(question["semantic_options"][question["label"]], row["solver"]["answer"])

    def test_llm_render_materialization_preserves_program_label(self) -> None:
        scaffold = generate_structured("log_both_boundaries", 3, 7)
        rendered = {
            "id": scaffold["id"],
            "context": "A synthetic audit log and its exact time-window rules are provided.",
            "question": "How many events satisfy all of the stated conditions?",
            "options": {key: f"Option value: {value}" for key, value in scaffold["question_spec"]["semantic_options"].items()},
        }
        self.assertFalse(local_render_problems(scaffold, rendered))
        row = materialize(scaffold, rendered, "deepseek-v4-flash")
        self.assertEqual(row["questions"]["decision"]["label"], scaffold["question_spec"]["label"])
        self.assertEqual(row["_meta"]["structured_state_sha256"], scaffold["_meta"]["state_sha256"])

    def test_llm_response_parsers(self) -> None:
        item = {"id": "x", "context": "c", "question": "q", "options": {"a": "A", "b": "B"}}
        self.assertEqual(parse_items({"items": [item]})["x"], item)
        accepted, issues = parse_audit({"items": [{"id": "x", "faithful": True, "issues": []}]})
        self.assertEqual(accepted, {"x"})
        self.assertEqual(issues, {})


if __name__ == "__main__":
    unittest.main()
