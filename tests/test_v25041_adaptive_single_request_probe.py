from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v25041_adaptive_single_request_probe as target  # noqa: E402


PROVIDER_KEYS = (
    "calls",
    "hosted_search_attempts",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "fetch_calls",
    "fetch_failures",
    "recursive_split_requests",
    "transport_failures",
    "hard_total_wall_timeouts",
)


def provider(*, calls: int, input_tokens: int, total_tokens: int) -> dict[str, int]:
    value = {name: 0 for name in PROVIDER_KEYS}
    value.update(
        {
            "calls": calls,
            "hosted_search_attempts": calls,
            "tool_calls": calls,
            "input_tokens": input_tokens,
            "output_tokens": total_tokens - input_tokens,
            "total_tokens": total_tokens,
        }
    )
    return value


def row(pair: int) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v25041_adaptive_single_request_task_result",
        "protocol_id": target.PROTOCOL_ID,
        "pair": pair,
        "terminal": True,
        "failure_stage": None,
        "candidate_trace": {
            "web_search_action_count": 4,
            "nonquery_action_count": 0,
            "distinct_action_query_count": 4,
            "seed_exact_first_order": True,
            "mixed_seed_followup_action_count": 0,
            "seed_action_after_followup_count": 0,
            "followup_query_count": 2,
            "followups_with_seed_anchor": 2,
            "followups_with_seed_title_novel_token": 2,
            "seed_source_count": 4,
            "seed_source_title_count": 4,
            "total_distinct_action_sources": 5,
            "trace_capability_passed": True,
            "query_title_url_payload_or_credential_persisted": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "candidate_provider": provider(calls=1, input_tokens=100, total_tokens=110),
        "control_provider": provider(calls=2, input_tokens=150, total_tokens=165),
        "control_exact_query_vectors": 2,
        "candidate_distinct_action_sources": 5,
        "control_distinct_action_sources": 4,
        "same_candidate_generated_four_query_vector_used_by_control": True,
        "wall_seconds": 1.0,
        "query_title_url_page_provider_payload_or_credential_persisted": False,
        "benchmark_manifest_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "page_fetch_generation_model_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    return target.validate_row(target.seal(value, "row_payload_sha256"))


class V25041AdaptiveProbeTests(unittest.TestCase):
    def test_population_is_consumed_pairs_five_through_eight(self) -> None:
        self.assertEqual(target.PAIR_NUMBERS, (5, 6, 7, 8))
        self.assertEqual(len(target.selected_queries()), 4)
        binding = target.parent_binding()
        self.assertTrue(binding["selected_pairs_previously_consumed"])
        self.assertTrue(binding["selected_pairs_excluded_from_future_confirmation"])

    def test_synthetic_aggregate_passes_all_capability_cost_source_gates(self) -> None:
        rows = [row(pair) for pair in target.PAIR_NUMBERS]
        aggregate = target.aggregate(rows, wall_seconds=2.0)
        decision = target.decision(aggregate)
        self.assertTrue(decision["capability_cost_source_gate_passed"])
        self.assertTrue(decision["fresh_external_gate_design_authorized"])
        self.assertFalse(decision["fresh_external_or_benchmark_effect_authorized"])

    def test_cost_regression_fails_without_weakening_other_checks(self) -> None:
        rows = [row(pair) for pair in target.PAIR_NUMBERS]
        rows[0] = copy.deepcopy(rows[0])
        rows[0]["candidate_provider"]["input_tokens"] = 1000
        rows[0]["candidate_provider"]["total_tokens"] = 1010
        rows[0] = target.seal(rows[0], "row_payload_sha256")
        aggregate = target.aggregate(rows, wall_seconds=2.0)
        decision = target.decision(aggregate)
        self.assertFalse(decision["capability_cost_source_gate_passed"])
        self.assertIn("candidate_input_cost", decision["failed_checks"])
        self.assertIn("candidate_total_cost", decision["failed_checks"])

    def test_task_row_rejects_extra_content_surface(self) -> None:
        value = row(5)
        value["query"] = "forbidden"
        value = target.seal(value, "row_payload_sha256")
        with self.assertRaises(RuntimeError):
            target.validate_row(value)

    def test_recursive_forbidden_key_scan_finds_content_keys(self) -> None:
        self.assertEqual(target._forbidden_keys({"nested": {"query": "x"}}), {"query"})
        self.assertEqual(target._forbidden_keys({"counts": [1, 2]}), set())


if __name__ == "__main__":
    unittest.main()
