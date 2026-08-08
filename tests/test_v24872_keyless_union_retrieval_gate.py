from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24872_keyless_union_retrieval_gate as gate  # noqa: E402


class V24872KeylessUnionRetrievalGateTests(unittest.TestCase):
    def test_protocol_matches_20x4x10_fixed_budget_shape(self) -> None:
        value = gate.build_protocol(now=1, require_clean=False, require_pristine=False)
        self.assertEqual(value["provider"]["executor_concurrency"], 20)
        self.assertEqual(value["schedule"]["task_count"], 20)
        self.assertEqual(value["schedule"]["logical_queries_per_task"], 4)
        self.assertEqual(value["schedule"]["fetch_cap_per_task"], 10)
        self.assertEqual(value["gates"]["logical_queries"], 80)
        self.assertEqual(value["gates"]["fetches_attempted"], 200)
        self.assertFalse(value["authorization"]["benchmark_external_or_exact220_launch"])

    def test_query_vector_is_new_fixed_neutral_documentation_only(self) -> None:
        vector = gate.query_vector()
        self.assertEqual(len(vector), 20)
        self.assertTrue(all(len(row) == 4 for row in vector))
        self.assertTrue(all("official documentation" in query.casefold() for row in vector for query in row))

    def test_fixed_policy_disables_entropy_and_admits_full_delta(self) -> None:
        policy = gate.policy_dict()
        self.assertEqual(policy["information_gain_weight"], 0.0)
        self.assertEqual(policy["latency_loss_per_second"], 0.0)
        self.assertEqual(policy["minimum_net_value"], -1.0)
        self.assertEqual(policy["wave1_queries"] + policy["wave2_queries"], 4)
        self.assertEqual(policy["wave1_fetches"] + policy["wave2_fetches"], 10)

    def test_aggregate_gate_is_content_free_and_fail_closed(self) -> None:
        row = {
            "terminal": True, "completed": True, "logical_queries": 4,
            "fetches_attempted": 10, "usable_pages": 8, "novel_pages": 8,
            "unique_hosts": 6, "unrecoverable_search_failures": 0,
            "provider_response_calls": 2, "tool_calls": 2,
            "transport_failures": 0, "hosted_search_attempts": 2,
            "hosted_search_deadline_failures": 0, "hard_fetch_helper_calls": 10,
            "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0,
            "fetch_deadline_rejections": 0, "wall_seconds": 10.0,
        }
        value = gate._aggregate([dict(row) for _ in range(20)], 11.0)
        self.assertTrue(gate._passed(value))
        self.assertFalse(value["contains_query_url_title_snippet_page_answer_provider_payload_or_per_task_row"])
        value["minimum_task_usable_pages"] = 5
        self.assertFalse(gate._passed(value))

    def test_source_has_no_evaluator_or_credential_capability(self) -> None:
        source = (ROOT / "scripts/v24872_keyless_union_retrieval_gate.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertNotIn("os.environ", source)


if __name__ == "__main__":
    unittest.main()
