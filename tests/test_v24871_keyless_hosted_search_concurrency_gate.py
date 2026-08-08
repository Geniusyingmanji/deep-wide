from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24871_keyless_hosted_search_concurrency_gate as gate  # noqa: E402


class V24871KeylessHostedSearchConcurrencyGateTests(unittest.TestCase):
    def test_schedule_matches_intended_full_run_concurrency_shape(self) -> None:
        value = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["schedule"]["task_count"], 20)
        self.assertEqual(value["schedule"]["executor_concurrency"], 20)
        self.assertEqual(value["schedule"]["logical_queries_per_task"], 4)
        self.assertEqual(value["schedule"]["total_logical_queries"], 80)
        self.assertFalse(
            value["authorization"]["benchmark_external_or_exact220_launch"]
        )

    def test_query_vector_is_fixed_neutral_and_has_exact_shape(self) -> None:
        vector = gate.query_vector()
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        self.assertTrue(
            all(
                "official" in query.casefold()
                for row in vector
                for query in row
            )
        )

    def test_aggregate_and_gate_are_content_free_and_fail_closed(self) -> None:
        row = {
            "terminal": True,
            "successful_task": True,
            "logical_query_rows": 4,
            "successful_query_rows": 4,
            "failed_query_rows": 0,
            "provider_response_calls": 1,
            "tool_calls": 1,
            "transport_failures": 0,
            "hosted_search_attempts": 1,
            "hosted_search_deadline_failures": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "wall_seconds": 1.0,
        }
        aggregate = gate._aggregate([dict(row) for _ in range(20)], 1.5)
        protocol = gate.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        self.assertTrue(gate._passed(aggregate, protocol["gates"]))
        self.assertFalse(
            aggregate[
                "contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row"
            ]
        )
        aggregate["failed_task_count"] = 1
        self.assertFalse(gate._passed(aggregate, protocol["gates"]))

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (
            ROOT / "scripts/v24871_keyless_hosted_search_concurrency_gate.py"
        ).read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
