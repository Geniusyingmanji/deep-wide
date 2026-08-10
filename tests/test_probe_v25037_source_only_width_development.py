from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import probe_v25037_source_only_width_development as target  # noqa: E402


def row(width: int) -> dict:
    arm = f"width_{width}"
    calls = 4 // width
    tokens = {1: 4000, 2: 3200, 4: 2800}[width]
    sources = {1: 20, 2: 19, 4: 18}[width]
    distinct = {1: 18, 2: 17, 4: 16}[width]
    return {
        "arm": arm,
        "width": width,
        "chunk_count": calls,
        "terminal": True,
        "failure_type": None,
        "wall_seconds": float(calls),
        "provider_counters": {
            "calls": calls,
            "failures": 4,
            "tool_calls": calls,
            "fetch_calls": 0,
            "fetch_failures": 0,
            "input_tokens": tokens,
            "output_tokens": 40 * calls,
            "total_tokens": tokens + 40 * calls,
            "hosted_search_attempts": calls,
            "hard_total_wall_timeouts": 0,
            "observed_action_query_count": 4,
            "observed_exact_action_query_count": 4,
            "fully_observed_request_query_vectors": calls,
        },
        "logical_query_count": 4,
        "raw_query_local_result_count": 0,
        "raw_action_source_count": sources,
        "raw_query_local_mapping_failure_count": 4,
        "raw_unrecoverable_failure_count": 0,
        "union_source_count": sources,
        "distinct_union_source_count": distinct,
        "recursive_split_requests": 0,
        "query_url_page_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    }


def execution() -> dict:
    watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in target.base.EXPECTED_WATCHERS
    ]
    return {
        "git_head": "1" * 40,
        "target_main": "1" * 40,
        "runtime_manifest": {
            relative: "2" * 64 for relative in target.RUNTIME_FILES
        },
        "protected_watchers_before": watchers,
        "protected_watchers_after": copy.deepcopy(watchers),
        "active_conflict_pids": [],
        "loopback_gpt56_port_ready": True,
        "shared_api_lease_acquired": True,
        "shared_api_lease_owner": "v25037_source_only_width_development_v1",
    }


class V25037WidthDevelopmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [row(width) for width in target.WIDTHS]
        self.parent = target._parent_binding()
        self.execution = execution()

    def result(self, rows: list[dict] | None = None) -> dict:
        return target.build_result(
            self.rows if rows is None else rows,
            batch_wall_seconds=4.0,
            parent_binding=self.parent,
            execution=self.execution,
        )

    def test_schedule_uses_same_four_consumed_queries_at_each_width(self) -> None:
        vector = target._query_vector()
        self.assertEqual(len(vector), 4)
        for width in target.WIDTHS:
            chunks = target.chunks_for_width(width)
            self.assertEqual(len(chunks), 4 // width)
            self.assertEqual(tuple(item for chunk in chunks for item in chunk), vector)
        self.assertEqual(self.parent["consumed_pair_numbers"], [3, 4])
        self.assertEqual(self.parent["consumed_terminal_arm_rows"], 4)

    def test_synthetic_width_amortization_gate_passes_without_launch_authority(self) -> None:
        value = self.result()
        self.assertTrue(value["passed"])
        ratios = value["aggregate"]["ratios"]["width_4_over_width_1"]
        self.assertEqual(ratios["input_tokens"], 0.7)
        self.assertAlmostEqual(ratios["distinct_union_source_count"], 16 / 18)
        self.assertTrue(value["authorization"]["fresh_width_matched_gate_design"])
        self.assertFalse(value["authorization"]["confirmation_or_benchmark_launch"])
        self.assertFalse(value["authorization"]["dev64_or_exact220"])

    def test_retry_query_loss_and_source_loss_fail_closed(self) -> None:
        for mode in ("retry", "query", "source"):
            rows = copy.deepcopy(self.rows)
            candidate = rows[-1]
            if mode == "retry":
                candidate["provider_counters"]["hosted_search_attempts"] = 2
            elif mode == "query":
                candidate["provider_counters"]["observed_exact_action_query_count"] = 3
                candidate["provider_counters"]["fully_observed_request_query_vectors"] = 0
            else:
                candidate["union_source_count"] = 10
                candidate["distinct_union_source_count"] = 6
            value = self.result(rows)
            self.assertFalse(value["passed"])

    def test_nonmonotonic_or_weak_cost_direction_fails_closed(self) -> None:
        rows = copy.deepcopy(self.rows)
        rows[-1]["provider_counters"]["input_tokens"] = 3900
        rows[-1]["provider_counters"]["total_tokens"] = 3940
        value = self.result(rows)
        self.assertFalse(value["checks"]["input_tokens_monotonic_with_width"])
        self.assertFalse(value["checks"]["width_4_input_token_amortization"])
        self.assertFalse(value["passed"])

    def test_duplicate_arm_and_tampered_aggregate_are_rejected(self) -> None:
        duplicate = copy.deepcopy(self.rows)
        duplicate[-1] = copy.deepcopy(duplicate[0])
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.result(duplicate)
        value = self.result()
        value["aggregate"]["arms"]["width_4"]["distinct_union_source_count"] += 1
        value["result_payload_sha256"] = target.base.payload_sha256(
            {key: item for key, item in value.items() if key != "result_payload_sha256"}
        )
        with self.assertRaisesRegex(ValueError, "result drifted"):
            target.validate_result(value)

    def test_runtime_has_no_direct_benchmark_or_evaluator_import(self) -> None:
        path = ROOT / "scripts/probe_v25037_source_only_width_development.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        for forbidden in ("deepwidebench", "eval", "pandas", "requests"):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertNotIn("results.csv", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
