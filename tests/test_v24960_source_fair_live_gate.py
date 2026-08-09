from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24960_source_fair_live_gate as gate  # noqa: E402


def passing_row() -> dict[str, int | float | bool]:
    return {
        "terminal": True, "completed": True, "logical_query_rows": 4,
        "search_provider_attempts": 2, "search_provider_response_calls": 2,
        "search_http_2xx": 2, "transport_failures": 0,
        "hosted_search_deadline_failures": 0, "raw_action_group_count": 4,
        "raw_action_source_count": 24, "matched_selection": True,
        "control_selected_leads": 10, "candidate_selected_leads": 10,
        "selection_changed": True, "control_registrable_sources": 6,
        "candidate_registrable_sources": 8, "registrable_source_coverage_gain": 2,
        "source_coverage_gain_task": True, "control_usable_pages": 8,
        "candidate_usable_pages": 8, "control_usable_chars": 30000,
        "candidate_usable_chars": 28000, "physical_union_fetches": 16,
        "hard_fetch_helper_calls": 16, "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0, "fetch_deadline_rejections": 0,
        "input_tokens": 100, "output_tokens": 50, "total_tokens": 150,
        "wall_seconds": 20.0,
    }


class V24960SourceFairLiveGateTests(unittest.TestCase):
    def test_protocol_freezes_fresh_shared_response_shape(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False, require_watchers=False
        )
        self.assertEqual(value["schedule"]["task_count"], 20)
        self.assertEqual(value["schedule"]["executor_concurrency"], 20)
        self.assertEqual(value["schedule"]["wave_fetch_caps"], [6, 4])
        self.assertEqual(value["schedule"]["fetch_cap_per_arm"], 10)
        self.assertTrue(value["schedule"]["shared_response_replay"])
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])

    def test_query_population_is_fixed_fresh_and_neutral(self) -> None:
        vector = gate.query_vector()
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        self.assertTrue(all("official documentation" in query.casefold() for row in vector for query in row))
        self.assertNotEqual(gate.payload_sha256(vector), gate.payload_sha256(gate.base.query_vector()))

    def test_registrable_source_counter_collapses_subdomains(self) -> None:
        leads = [
            {"url": "https://docs.alpha.example/a"},
            {"url": "https://news.alpha.example/b"},
            {"url": "https://beta.example/c"},
        ]
        self.assertEqual(gate._registrable_sources(leads), {"alpha.example", "beta.example"})

    def test_aggregate_gate_passes_strict_gain_and_fails_regression(self) -> None:
        aggregate = gate._aggregate([passing_row() for _ in range(20)], 30.0)
        decision = gate.decision(aggregate)
        self.assertTrue(decision["source_fair_live_gate_go"])
        self.assertFalse(aggregate["contains_query_url_host_title_page_answer_provider_payload_selection_or_per_task_row"])
        aggregate["candidate_usable_pages"] = int(aggregate["control_usable_pages"] * 0.90)
        decision = gate.decision(aggregate)
        self.assertFalse(decision["source_fair_live_gate_go"])
        self.assertIn("candidate_usable_pages_bounded", decision["failed_checks"])

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (ROOT / "scripts/v24960_source_fair_live_gate.py").read_text(encoding="utf-8")
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
