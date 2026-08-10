from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25038_batching_external_contract as contract  # noqa: E402
from deepwide_agent import v25038_source_only_batching as batching  # noqa: E402
from scripts import run_v25038_batching_external as runner  # noqa: E402


class V25038BatchingExternalTests(unittest.TestCase):
    def test_population_and_query_vector_are_visible_only_and_fixed(self) -> None:
        tasks = contract.task_vector()
        queries = contract.query_vector()
        self.assertEqual(len(tasks), contract.TASK_COUNT)
        self.assertEqual(len(queries), contract.TASK_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all(len(row) == 4 and len(set(row)) == 4 for row in queries))
        self.assertEqual(len(set(contract.PROJECTS)), contract.TASK_COUNT)

    def test_query_batching_preserves_same_vector_and_only_changes_grouping(self) -> None:
        queries = contract.query_vector()[0]
        control = batching.query_chunks(queries, contract.CONTROL_ARM)
        candidate = batching.query_chunks(queries, contract.CANDIDATE_ARM)
        self.assertEqual([len(chunk) for chunk in control], [2, 2])
        self.assertEqual([len(chunk) for chunk in candidate], [4])
        self.assertEqual(tuple(item for chunk in control for item in chunk), tuple(queries))
        self.assertEqual(tuple(item for chunk in candidate for item in chunk), tuple(queries))

    def test_shared_fetch_union_is_stable_and_deduplicated(self) -> None:
        values = {
            contract.CONTROL_ARM: [
                {"url": "https://a.example/x", "fetch_url": "https://a.example/x", "title": "A"},
                {"url": "https://b.example/y", "fetch_url": "https://b.example/y", "title": "B"},
            ],
            contract.CANDIDATE_ARM: [
                {"url": "https://b.example/y", "fetch_url": "https://b.example/y", "title": "B2"},
                {"url": "https://c.example/z", "fetch_url": "https://c.example/z", "title": "C"},
            ],
        }
        requests = batching.shared_fetch_requests(values)
        self.assertEqual([item["url"] for item in requests], [
            "https://a.example/x", "https://b.example/y", "https://c.example/z"
        ])
        reversed_requests = batching.shared_fetch_requests(
            values, arm_order=contract.ARMS[::-1]
        )
        self.assertEqual([item["url"] for item in reversed_requests], [
            "https://b.example/y", "https://c.example/z", "https://a.example/x"
        ])

    def test_fixed_evidence_requires_page_and_character_floor(self) -> None:
        leads = [
            {"url": "https://a.example/x", "fetch_url": "https://a.example/x"},
            {"url": "https://b.example/y", "fetch_url": "https://b.example/y"},
        ]
        fetched = {
            "https://a.example/x": {"raw_content": "a" * 80, "title": "A"},
            "https://b.example/y": {"raw_content": "b" * 80, "title": "B"},
        }
        evidence, observation = batching.build_fixed_evidence(
            leads, fetched, character_budget=100,
            minimum_usable_pages=2, minimum_raw_characters=150,
        )
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence or ""), 100)
        self.assertEqual(observation["usable_pages"], 2)
        missing, _ = batching.build_fixed_evidence(
            leads[:1], fetched, character_budget=100,
            minimum_usable_pages=2, minimum_raw_characters=150,
        )
        self.assertIsNone(missing)

    def test_normalizer_fails_closed_and_does_not_rewrite_fact_cells(self) -> None:
        raw = (
            "| Pkg | Version | Date | Python |\n"
            "|---|---|---|---|\n"
            "| demo | 1.2.3 | 2026-08-01 | >=3.10 |"
        )
        value, status = batching.normalize_prediction(
            raw, contract.COLUMNS, fallback=contract.FALLBACK_TABLE
        )
        self.assertNotEqual(status, "fallback")
        self.assertIn("1.2.3", value)
        fallback, status = batching.normalize_prediction(
            "not a table", contract.COLUMNS, fallback=contract.FALLBACK_TABLE
        )
        self.assertEqual(status, "fallback")
        self.assertEqual(fallback, contract.FALLBACK_TABLE)

    def test_protocol_freezes_no_evaluator_and_no_public_benchmark_authority(self) -> None:
        value = {
            "execution": {
                "only_treatment": "physical_query_grouping_split_2_plus_2_vs_one_shot_4"
            },
            "authorization": {"deepwidebench_dev64_exact220_or_sota": False},
            "source_policy": contract.source_policy(),
        }
        self.assertEqual(value["execution"]["only_treatment"],
                         "physical_query_grouping_split_2_plus_2_vs_one_shot_4")
        self.assertFalse(
            value["authorization"]["deepwidebench_dev64_exact220_or_sota"]
        )
        self.assertTrue(value["source_policy"]["prediction_freeze_before_gold_or_evaluator"])

    def _aggregate(self) -> dict[str, object]:
        control, candidate = contract.ARMS
        value: dict[str, object] = {
            "terminal_task_count": 20,
            "completed_task_count": 20,
            "failure_as_zero_task_count": 0,
            "shared_fetch_attempts": 180,
            "shared_fetch_successes": 170,
            "hard_fetch_helper_calls": 180,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
            "fetch_deadline_rejections": 0,
            "model_hard_total_wall_timeouts": 0,
        }
        for arm, calls, input_tokens, total_tokens, leads, pages, chars in (
            (control, 40, 200_000, 202_000, 180, 150, 900_000),
            (candidate, 20, 150_000, 152_000, 170, 145, 880_000),
        ):
            value[f"{arm}_logical_query_count"] = 80
            value[f"{arm}_provider_calls"] = calls
            value[f"{arm}_provider_attempts"] = calls
            value[f"{arm}_input_tokens"] = input_tokens
            value[f"{arm}_total_tokens"] = total_tokens
            value[f"{arm}_selected_lead_count"] = leads
            value[f"{arm}_usable_pages"] = pages
            value[f"{arm}_raw_characters"] = chars
            value[f"{arm}_observed_exact_action_query_count"] = 80
            value[f"{arm}_evidence_characters"] = 20 * contract.EVIDENCE_CHARS
            value[f"{arm}_model_attempts"] = 20
            value[f"{arm}_model_success"] = 20
            for name in (
                "raw_unrecoverable_failure_count", "recursive_split_requests",
                "transport_failures", "hard_total_wall_timeouts",
            ):
                value[f"{arm}_{name}"] = 0
        return value

    def test_mechanism_gate_requires_cost_and_all_yield_nonregression(self) -> None:
        aggregate = self._aggregate()
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        bad = copy.deepcopy(aggregate)
        bad[f"{contract.CANDIDATE_ARM}_usable_pages"] = 100
        decision = runner.mechanism_decision(bad)
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("candidate_usable_page_yield", decision["failed_checks"])

    def test_mechanism_gate_rejects_retry_query_loss_or_cost_miss(self) -> None:
        for mode in ("retry", "query", "cost"):
            aggregate = copy.deepcopy(self._aggregate())
            arm = contract.CANDIDATE_ARM
            if mode == "retry":
                aggregate[f"{arm}_provider_attempts"] = 21
            elif mode == "query":
                aggregate[f"{arm}_observed_exact_action_query_count"] = 79
            else:
                aggregate[f"{arm}_input_tokens"] = 190_000
            self.assertFalse(
                runner.mechanism_decision(aggregate)["mechanism_gate_passed"]
            )

    def test_task_row_rejects_privileged_or_content_surface_tamper(self) -> None:
        task = contract.task_vector()[0]
        row = {
            "artifact_version": 1,
            "role": "v25038_batching_external_task_result",
            "protocol_id": contract.PROTOCOL_ID,
            "opaque_id": task["opaque_id"],
            "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
            "terminal": True,
            "completed": False,
            "failure_as_zero": True,
            "failure_stage": "synthetic",
            "arm_order": [contract.CONTROL_ARM, contract.CANDIDATE_ARM],
            "search": {},
            "selected_leads": {arm: 0 for arm in contract.ARMS},
            "shared_fetch_attempts": 0,
            "shared_fetch_successes": 0,
            "fetch_health": {
                "hard_fetch_helper_calls": 0,
                "hard_fetch_deadline_failures": 0,
                "fetch_helper_failures": 0,
                "fetch_deadline_rejections": 0,
            },
            "evidence": {arm: {} for arm in contract.ARMS},
            "model_success": {arm: False for arm in contract.ARMS},
            "model_attempts": {arm: 0 for arm in contract.ARMS},
            "model_usage": {arm: {} for arm in contract.ARMS},
            "model_hard_total_wall_timeouts": 0,
            "normalizer_status": {arm: "fallback" for arm in contract.ARMS},
            "predictions": {arm: contract.FALLBACK_TABLE for arm in contract.ARMS},
            "prediction_sha256": {arm: contract.payload_sha256(contract.FALLBACK_TABLE) for arm in contract.ARMS},
            "prediction_changed": False,
            "wall_seconds": 0.1,
            "same_four_visible_queries_per_arm": True,
            "only_treatment_split_2_plus_2_vs_one_shot_4": True,
            "search_and_model_arm_first_position_balanced_by_preoutcome_opaque_hash": True,
            "shared_fetch_union_uses_same_preoutcome_arm_order": True,
            "shared_task_local_union_fetch_for_both_arms": True,
            "same_fixed_evidence_budget_prompt_model_output_cap_and_deadline": True,
            "provider_narrative_or_snippet_used_as_active_evidence": False,
            "query_url_host_title_page_provider_payload_or_credential_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "pypi_gold_endpoint_opened": False,
            "entropy_or_information_gain_assigns_credit_or_routes": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        sealed = contract.seal(row, "result_payload_sha256")
        runner.validate_task_row(sealed)
        sealed["query"] = "forbidden"
        sealed = contract.seal(sealed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(sealed)

    def test_watcher_snapshot_rejects_start_tick_or_marker_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, ticks, marker in contract.EXPECTED_WATCHERS:
                path = root / str(pid)
                path.mkdir()
                (path / "stat").write_text(
                    f"{pid} (python) S " + " ".join(["0"] * 18 + [str(ticks)])
                )
                (path / "cmdline").write_bytes(marker.encode() + b"\0")
            contract.watcher_snapshot(root)
            first = contract.EXPECTED_WATCHERS[0][0]
            (root / str(first) / "cmdline").write_bytes(b"wrong\0")
            with self.assertRaises(RuntimeError):
                contract.watcher_snapshot(root)


if __name__ == "__main__":
    unittest.main()
