from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24962_cumulative_source_fair_live_gate as gate  # noqa: E402


def passing_row() -> dict[str, int | float | bool]:
    return {
        "terminal": True, "completed": True, "logical_query_rows": 4,
        "search_provider_attempts": 2, "search_provider_response_calls": 2,
        "search_http_2xx": 2, "transport_failures": 0,
        "hosted_search_deadline_failures": 0, "raw_action_group_count": 4,
        "raw_action_source_count": 24, "matched_selection": True,
        "control_selected_leads": 10, "candidate_selected_leads": 10,
        "selection_changed": True, "control_registrable_sources": 5,
        "candidate_registrable_sources": 7, "registrable_source_coverage_gain": 2,
        "source_coverage_gain_task": True, "control_usable_pages": 8,
        "candidate_usable_pages": 8, "control_usable_chars": 30000,
        "candidate_usable_chars": 28000, "planned_shared_url_union_count": 16,
        "actual_hard_fetch_helper_calls": 16, "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0, "fetch_deadline_rejections": 0,
        "input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
        "wall_seconds": 20.0,
    }


class V24962CumulativeSourceFairLiveGateTests(unittest.TestCase):
    def test_protocol_freezes_fresh_cumulative_shape(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False, require_watchers=False
        )
        self.assertEqual(value["schedule"]["task_count"], 20)
        self.assertEqual(value["schedule"]["wave_fetch_caps"], [6, 4])
        self.assertEqual(value["schedule"]["fetch_cap_per_arm"], 10)
        self.assertTrue(value["schedule"]["cumulative_two_wave_source_guard"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])

    def test_query_population_is_fresh_against_both_parents(self) -> None:
        vector = gate.query_vector()
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        digest = gate.payload_sha256(vector)
        self.assertNotEqual(digest, gate.payload_sha256(gate.parent.query_vector()))
        self.assertNotEqual(digest, gate.payload_sha256(gate.parent.base.query_vector()))

    def test_aggregate_gate_distinguishes_planned_and_actual_fetches(self) -> None:
        aggregate = gate._aggregate([passing_row() for _ in range(20)], 30.0)
        self.assertTrue(gate.decision(aggregate)["cumulative_source_fair_live_gate_go"])
        aggregate["actual_hard_fetch_helper_calls"] -= 1
        decision = gate.decision(aggregate)
        self.assertFalse(decision["cumulative_source_fair_live_gate_go"])
        self.assertIn("planned_union_equals_actual_helpers", decision["failed_checks"])

    def test_gate_rejects_incomplete_second_wave_signature(self) -> None:
        aggregate = gate._aggregate([passing_row() for _ in range(20)], 30.0)
        aggregate["completed_task_count"] = 15
        aggregate["logical_query_rows"] = 70
        decision = gate.decision(aggregate)
        self.assertFalse(decision["cumulative_source_fair_live_gate_go"])
        self.assertIn("all_tasks_completed", decision["failed_checks"])
        self.assertIn("all_logical_query_rows_committed", decision["failed_checks"])

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (
            ROOT / "scripts/v24962_cumulative_source_fair_live_gate.py"
        ).read_text(encoding="utf-8")
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
