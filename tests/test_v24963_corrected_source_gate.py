from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24963_corrected_source_gate as gate  # noqa: E402


class V24963CorrectedSourceGateTests(unittest.TestCase):
    def test_gate_replaces_control_floor_with_candidate_capability(self) -> None:
        values = gate.gates()
        self.assertNotIn("minimum_control_registrable_sources", values)
        self.assertEqual(values["minimum_candidate_registrable_sources"], 80)
        self.assertEqual(values["minimum_candidate_over_control_registrable_source_ratio"], 1.25)
        self.assertEqual(values["minimum_candidate_over_control_usable_page_ratio"], 0.90)

    def test_protocol_preserves_parent_no_go_and_authorizes_no_launch(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False, require_watchers=False
        )
        self.assertTrue(value["parent_observation"]["parent_remains_no_go"])
        self.assertEqual(value["parent_observation"]["failed_checks"], ["control_source_coverage_present"])
        self.assertEqual(value["gate_correction"]["replacement_value"], 80)
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_query_population_is_fresh_against_three_predecessors(self) -> None:
        vector = gate.query_vector()
        digest = gate.payload_sha256(vector)
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        self.assertNotEqual(digest, gate.payload_sha256(gate.parent.query_vector()))
        self.assertNotEqual(digest, gate.payload_sha256(gate.parent.parent.query_vector()))
        self.assertNotEqual(digest, gate.payload_sha256(gate.parent.parent.base.query_vector()))

    def test_parent_probe_is_closure_free_isolated_and_unmodified(self) -> None:
        original = gate.parent.query_vector
        clone = gate.isolated_probe()
        self.assertIsNone(gate.parent._probe.__closure__)
        self.assertIs(clone.__globals__["query_vector"], gate.query_vector)
        self.assertIs(gate.parent.query_vector, original)
        self.assertIsNot(gate.parent.query_vector, gate.query_vector)

    def test_corrected_decision_uses_candidate_floor_not_control_floor(self) -> None:
        row = {
            "terminal": True, "completed": True, "logical_query_rows": 4,
            "search_provider_attempts": 2, "search_provider_response_calls": 2,
            "search_http_2xx": 2, "transport_failures": 0,
            "hosted_search_deadline_failures": 0, "raw_action_group_count": 4,
            "raw_action_source_count": 24, "matched_selection": True,
            "control_selected_leads": 10, "candidate_selected_leads": 10,
            "selection_changed": True, "control_registrable_sources": 2,
            "candidate_registrable_sources": 5, "registrable_source_coverage_gain": 3,
            "source_coverage_gain_task": True, "control_usable_pages": 8,
            "candidate_usable_pages": 8, "control_usable_chars": 30000,
            "candidate_usable_chars": 28000, "planned_shared_url_union_count": 16,
            "actual_hard_fetch_helper_calls": 16, "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0, "fetch_deadline_rejections": 0,
            "input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
            "wall_seconds": 20.0,
        }
        aggregate = gate._aggregate([dict(row) for _ in range(20)], 30.0)
        decision = gate.decision(aggregate)
        self.assertTrue(decision["corrected_source_capability_gate_go"])
        aggregate["candidate_registrable_sources"] = 79
        decision = gate.decision(aggregate)
        self.assertFalse(decision["corrected_source_capability_gate_go"])
        self.assertIn("candidate_absolute_source_capability", decision["failed_checks"])

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (ROOT / "scripts/v24963_corrected_source_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("os.environ", source)
        self.assertIsNone(gate.SECRET.search(source))


if __name__ == "__main__":
    unittest.main()
