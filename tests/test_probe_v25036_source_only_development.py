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

from scripts import probe_v25036_source_only_development as target  # noqa: E402


def row(pair: int, arm: str) -> dict:
    candidate = arm == "source_only"
    input_tokens = 800 if candidate else 1000
    output_tokens = 80 if candidate else 200
    return {
        "pair": pair,
        "arm": arm,
        "terminal": True,
        "failure_type": None,
        "wall_seconds": 0.8 if candidate else 1.0,
        "provider_counters": {
            "calls": 1,
            "failures": 0,
            "tool_calls": 2,
            "fetch_calls": 0,
            "fetch_failures": 0,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "hosted_search_attempts": 1,
            "hard_total_wall_timeouts": 0,
            "observed_action_query_count": 2,
            "observed_exact_action_query_count": 2,
            "fully_observed_request_query_vectors": 1,
        },
        "logical_query_count": 2,
        "raw_query_local_result_count": 0,
        "raw_action_source_count": 4,
        "raw_query_local_mapping_failure_count": 2,
        "raw_unrecoverable_failure_count": 0,
        "union_source_count": 4,
        "recursive_split_requests": 0,
        "query_url_page_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_evaluator_score_or_reward_read": False,
    }


def execution() -> dict:
    watchers = [
        {"pid": pid, "start_ticks": ticks, "marker": marker}
        for pid, ticks, marker in target.EXPECTED_WATCHERS
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
        "shared_api_lease_owner": "v25036_source_only_development_probe_v1",
    }


class V25036DevelopmentProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            row(pair, arm)
            for pair in (1, 2)
            for arm in target.ARMS
        ]
        self.parent = target._parent_binding()
        self.execution = execution()

    def result(self, rows: list[dict] | None = None) -> dict:
        return target.build_result(
            self.rows if rows is None else rows,
            wall=2.0,
            parent_binding=self.parent,
            execution=self.execution,
        )

    def test_parent_binding_proves_pairs_were_already_consumed(self) -> None:
        self.assertEqual(self.parent["consumed_pair_count"], 2)
        self.assertEqual(self.parent["consumed_terminal_arm_rows"], 4)
        self.assertTrue(
            self.parent["consumed_pairs_permanently_excluded_from_confirmation"]
        )
        self.assertEqual(
            self.parent["query_set_sha256"], target.EXPECTED_QUERY_SET_SHA256
        )

    def test_synthetic_directional_gate_passes_and_keeps_authority_false(self) -> None:
        value = self.result()
        self.assertTrue(value["passed"])
        self.assertTrue(value["checks"]["all_exact_action_queries_observed"])
        self.assertEqual(
            value["aggregate"]["source_only_over_production_summary"][
                "input_tokens"
            ],
            0.8,
        )
        self.assertTrue(
            value["authorization"]["fresh_source_only_confirmation_gate_design"]
        )
        self.assertFalse(value["authorization"]["confirmation_or_benchmark_launch"])
        self.assertFalse(value["authorization"]["dev64_or_exact220"])

    def test_provider_failures_do_not_overwrite_arm_exception_count(self) -> None:
        rows = copy.deepcopy(self.rows)
        rows[0]["provider_counters"]["failures"] = 2
        rows[0]["failure_type"] = "SearchRequestError"
        value = self.result(rows)
        control = value["aggregate"]["production_summary"]
        self.assertEqual(control["failures"], 2)
        self.assertEqual(control["arm_exceptions"], 1)
        self.assertFalse(value["checks"]["no_arm_exception"])
        self.assertFalse(value["passed"])

    def test_missing_exact_action_query_or_source_yield_fails_closed(self) -> None:
        for mutate in ("query", "yield"):
            rows = copy.deepcopy(self.rows)
            for item in rows:
                if item["arm"] != "source_only":
                    continue
                if mutate == "query":
                    item["provider_counters"]["observed_exact_action_query_count"] = 1
                    item["provider_counters"]["fully_observed_request_query_vectors"] = 0
                else:
                    item["raw_action_source_count"] = 1
                    item["union_source_count"] = 1
            value = self.result(rows)
            self.assertFalse(value["passed"])

    def test_duplicate_rows_and_tampered_seal_are_rejected(self) -> None:
        duplicate = copy.deepcopy(self.rows)
        duplicate[-1]["pair"] = 1
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.result(duplicate)
        value = self.result()
        value["aggregate"]["source_only"]["union_sources"] += 1
        with self.assertRaisesRegex(ValueError, "result drifted"):
            target.validate_result(value)

    def test_runtime_has_no_direct_benchmark_or_evaluator_import(self) -> None:
        path = ROOT / "scripts/probe_v25036_source_only_development.py"
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
