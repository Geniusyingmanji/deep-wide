from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24956_neutral_dual_transport_gate as gate  # noqa: E402


def arm_row(arm: str) -> dict[str, int | float | bool | str]:
    return {
        "arm": arm,
        "terminal": True,
        "successful_task": True,
        "mapping_complete": True,
        "logical_query_rows": 2,
        "returned_query_rows": 2,
        "successful_query_rows": 2,
        "failed_query_rows": 0,
        "query_rows_with_url_citation": 2,
        "url_citations": 3,
        "annotation_url_citations": 3,
        "web_search_actions": 1,
        "action_sources": 3,
        "provider_attempts": 1,
        "provider_response_calls": 1,
        "http_2xx": 1,
        "http_4xx": 0,
        "http_5xx": 0,
        "transport_failures": 0,
        "hosted_search_deadline_failures": 0,
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "wall_seconds": 10.0,
    }


class V24956NeutralDualTransportGateTests(unittest.TestCase):
    def test_protocol_freezes_matched_content_free_shape(self) -> None:
        value = gate.build_protocol(
            now=1,
            require_clean=False,
            require_pristine=False,
            require_watchers=False,
        )
        self.assertEqual(value["schedule"]["tasks_per_arm"], 8)
        self.assertEqual(value["schedule"]["total_invocations"], 16)
        self.assertEqual(value["schedule"]["executor_concurrency"], 16)
        self.assertEqual(set(value["arms"]), {"control_9878", "candidate_8787"})
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_query_and_invocation_vectors_are_fixed_and_balanced(self) -> None:
        self.assertEqual(len(gate.query_vector()), 8)
        self.assertTrue(all(len(pair) == 2 for pair in gate.query_vector()))
        schedule = gate.invocation_schedule()
        self.assertEqual(len(schedule), 16)
        for arm in gate.ARMS:
            self.assertEqual(sum(name == arm for name, _ in schedule), 8)

    def test_aggregate_discards_rows_and_candidate_can_pass(self) -> None:
        rows = [
            arm_row(arm)
            for arm in gate.ARMS
            for _ in range(gate.TASKS_PER_ARM)
        ]
        aggregate = gate._aggregate(rows, 20.0)
        self.assertTrue(gate.decision(aggregate)["candidate_transport_go"])
        for arm in gate.ARMS:
            self.assertFalse(
                aggregate[arm][
                    "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row"
                ]
            )
            self.assertNotIn("rows", aggregate[arm])

    def test_relative_cost_or_missing_candidate_row_fails_closed(self) -> None:
        rows = [
            arm_row(arm)
            for arm in gate.ARMS
            for _ in range(gate.TASKS_PER_ARM)
        ]
        for row in rows:
            if row["arm"] == gate.CANDIDATE_ARM:
                row["total_tokens"] = 300
        aggregate = gate._aggregate(rows, 20.0)
        self.assertFalse(gate.decision(aggregate)["candidate_transport_go"])
        self.assertIn(
            "candidate_token_cost_bounded", gate.decision(aggregate)["failed_checks"]
        )
        aggregate[gate.CANDIDATE_ARM]["successful_query_rows"] = 15
        self.assertFalse(gate.decision(aggregate)["candidate_transport_go"])

    def test_runtime_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (ROOT / "scripts/v24956_neutral_dual_transport_gate.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        self.assertNotIn("os.environ", source)
        self.assertIsNone(gate.SECRET.search(source))


if __name__ == "__main__":
    unittest.main()
