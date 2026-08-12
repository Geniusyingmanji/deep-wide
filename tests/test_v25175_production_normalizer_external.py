from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as parser  # noqa: E402
from deepwide_agent import v25175_production_normalizer_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import control_v25175_production_normalizer_external as control  # noqa: E402
from scripts import run_v25175_production_normalizer_external as runner  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
)
from test_v25147_deterministic_quote_candidate_runtime import CandidateModel  # noqa: E402


SYNTHETIC_TASK = {
    "opaque_id": contract.task_vector()[0]["opaque_id"],
    "question": QUESTION,
}


class AccountingSyntheticSearch(GroundedFrontierSearch):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.actual_search_invocations = 0
        self.actual_logical_query_count = 0
        self.actual_fetch_invocations = 0
        self.actual_fetch_request_count = 0

    def search_many(self, queries, **kwargs):
        values = list(queries)
        self.actual_search_invocations += 1
        self.actual_logical_query_count += len(values)
        return super().search_many(values, **kwargs)

    def fetch_urls(self, requests):
        values = list(requests)
        self.actual_fetch_invocations += 1
        self.actual_fetch_request_count += len(values)
        return super().fetch_urls(values)


class MalformedProductionModel(CandidateModel):
    """Return one successful provider response rejected by the frozen parser."""

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 2:
            self.prompts.append((str(system), str(user), bool(json_mode)))
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            return ModelResult(
                text="production prose without a markdown table",
                usage={},
                response_id=None,
                attempts=1,
                output_truncated=False,
            )
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class V25175ProductionNormalizerExternalTests(unittest.TestCase):
    def _row(self, *, malformed: bool = False) -> dict:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = MalformedProductionModel() if malformed else CompatibleModel()
            model = runner._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: AccountingSyntheticSearch(
                    SYNTHETIC_TASK["question"], phase, field_page=False
                )
                for phase in contract.runtime.PHASES
            }
            value = contract.runtime.run_task(
                SYNTHETIC_TASK,
                model=model,
                searches=searches,
                limits=ScoreFirstLimits(**contract.LIMITS),
            )
            row = runner._from_runtime(
                SYNTHETIC_TASK,
                value,
                1.0,
                runner._health(),
                runner._actual_effect_snapshot(model, searches),
            )
        return runner.validate_task_row(row)

    def test_fresh_population_schema_and_history_literal_zero(self) -> None:
        tasks = contract.task_vector()
        selection = contract.validate_population_selection_audit(ROOT, tracked=False)
        self.assertTrue(selection["audit_valid"])
        self.assertEqual(selection["identity_history_zero_hit_count"], 20)
        self.assertEqual(
            selection["ordered_identity_vector_sha256"],
            contract.IDENTITY_SELECTION_SHA256,
        )
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(set(contract.CLUES)), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertTrue(
            all(
                parser.extract_exact_visible_columns(row["question"])
                == list(contract.COLUMNS)
                for row in tasks
            )
        )
        freshness = control._history_freshness()
        self.assertEqual(freshness["clue_count"], 20)
        self.assertTrue(freshness["all_exact_literal_zero_hit"])
        self.assertTrue(
            all(row["history_hit_count"] == 0 for row in freshness["rows"])
        )

    def test_gate_constants_are_localization_only(self) -> None:
        gate = contract.mechanism_gate()
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["observer_entry_tasks"], 20)
        self.assertEqual(gate["observer_completed_tasks"], 20)
        self.assertEqual(
            gate["minimum_production_model_generated_tasks_for_reliability"], 18
        )
        self.assertEqual(gate["maximum_production_fallback_tasks_for_reliability"], 2)
        self.assertEqual(gate["maximum_sparse_model_forwards_total"], 80)
        self.assertEqual(
            contract.quality_gate(),
            {
                "quality_evaluator_authorized": False,
                "localization_gate_cannot_establish_outer_utility": True,
                "successful_localization_only_authorizes_normalizer_repair_design": True,
                "binding_successor_design": False,
                "vertical_binding_policy_change": False,
            },
        )

    def test_synthetic_rows_bind_parent_normalizer_and_effect_parity(self) -> None:
        valid = self._row(malformed=False)
        invalid = self._row(malformed=True)
        for row, accepted in ((valid, True), (invalid, False)):
            receipt = row["content_free_receipt"]
            observation = receipt["production_normalizer_observation"]
            sparse = row["parent_result"]["parent_result"]["parent_result"]
            self.assertEqual(receipt["production_normalizer_observer_entry_count"], 1)
            self.assertEqual(
                receipt["production_normalizer_observer_completed_count"], 1
            )
            self.assertIs(
                observation["frozen_synthesis_contract_accepted"], accepted
            )
            self.assertIs(
                receipt["parent_production_provider_output_valid"], accepted
            )
            self.assertEqual(
                row["actual_effect_snapshot"]["model_logical_requests"],
                sparse["content_free_receipt"]["provider_forward_count"],
            )
        self.assertEqual(valid["prediction_kind"], "model_generated")
        self.assertEqual(invalid["prediction_kind"], "fallback")
        self.assertEqual(
            invalid["content_free_receipt"]["production_normalizer_observation"][
                "disposition_counts"
            ]["no_pipe_group_reject"],
            1,
        )

    def test_localization_go_is_orthogonal_to_production_reliability(self) -> None:
        dispositions = {
            name: 0 for name in contract.runtime.observer.DISPOSITION_NAMES
        }
        dispositions["exact_table_accepted"] = 9
        dispositions["no_pipe_group_reject"] = 11
        aggregate = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "production_model_generated_tasks": 9,
            "production_fallback_tasks": 11,
            "observer_entry_tasks": 20,
            "observer_completed_tasks": 20,
            "observer_failure_tasks": 0,
            "disposition_counts": dispositions,
            "nonzero_disposition_buckets": 2,
            "accepted_observation_tasks": 9,
            "rejected_observation_tasks": 11,
            "provider_output_truncated_tasks": 0,
            "parser_count_totals": {
                name: 0 for name in contract.runtime.observer.COUNT_NAMES
            },
            "disposition_accounting_error": 0,
            "parent_behavior_drift_tasks": 0,
            "physical_queries": 80,
            "physical_fetches": 200,
            "physical_model_forwards": 60,
            "model_provider_requests": 60,
            "model_provider_attempts": 60,
            "model_provider_successes": 60,
            "system_total_tokens": 1,
            "observed_all_task_model_logical_requests": 60,
            "observed_all_task_logical_queries": 80,
            "observed_all_task_fetch_requests": 200,
            "content_free_receipt_valid_tasks": 20,
            "outer_or_accounting_failure_tasks": 0,
            "terminal_transport_timeout_helper_or_model_hard_failures": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        }
        decision = runner.mechanism_decision(aggregate)
        self.assertTrue(decision["normalizer_localization_gate_passed"])
        self.assertFalse(decision["production_reliability_gate_passed"])
        self.assertTrue(decision["normalizer_repair_design"])
        self.assertFalse(decision["binding_successor_design"])
        aggregate = copy.deepcopy(aggregate)
        aggregate["production_model_generated_tasks"] = 20
        aggregate["production_fallback_tasks"] = 0
        aggregate["accepted_observation_tasks"] = 20
        aggregate["rejected_observation_tasks"] = 0
        aggregate["disposition_counts"]["exact_table_accepted"] = 20
        aggregate["disposition_counts"]["no_pipe_group_reject"] = 0
        aggregate["nonzero_disposition_buckets"] = 1
        decision = runner.mechanism_decision(aggregate)
        self.assertTrue(decision["normalizer_localization_gate_passed"])
        self.assertTrue(decision["production_reliability_gate_passed"])
        self.assertFalse(decision["normalizer_repair_design"])

    def test_gate_fails_closed_on_observer_parity_effect_or_credit_tamper(self) -> None:
        dispositions = {
            name: 0 for name in contract.runtime.observer.DISPOSITION_NAMES
        }
        dispositions["exact_table_accepted"] = 20
        base = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "production_model_generated_tasks": 20,
            "production_fallback_tasks": 0,
            "observer_entry_tasks": 20,
            "observer_completed_tasks": 20,
            "observer_failure_tasks": 0,
            "disposition_counts": dispositions,
            "nonzero_disposition_buckets": 1,
            "accepted_observation_tasks": 20,
            "rejected_observation_tasks": 0,
            "provider_output_truncated_tasks": 0,
            "parser_count_totals": {
                name: 0 for name in contract.runtime.observer.COUNT_NAMES
            },
            "disposition_accounting_error": 0,
            "parent_behavior_drift_tasks": 0,
            "physical_queries": 80,
            "physical_fetches": 200,
            "physical_model_forwards": 60,
            "model_provider_requests": 60,
            "model_provider_attempts": 60,
            "model_provider_successes": 60,
            "system_total_tokens": 1,
            "observed_all_task_model_logical_requests": 60,
            "observed_all_task_logical_queries": 80,
            "observed_all_task_fetch_requests": 200,
            "content_free_receipt_valid_tasks": 20,
            "outer_or_accounting_failure_tasks": 0,
            "terminal_transport_timeout_helper_or_model_hard_failures": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        }
        self.assertTrue(
            runner.mechanism_decision(base)["normalizer_localization_gate_passed"]
        )
        for field, value in (
            ("observer_failure_tasks", 1),
            ("disposition_accounting_error", 1),
            ("parent_behavior_drift_tasks", 1),
            ("physical_queries", 79),
            ("physical_fetches", 281),
            ("physical_model_forwards", 81),
            ("positive_signed_credit_count", 1),
        ):
            changed = copy.deepcopy(base)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                runner.mechanism_decision(changed)

    def test_contract_runner_and_controller_are_label_blind_evaluator_free(self) -> None:
        privileged_names = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for relative in (contract.CONTRACT, contract.RUNNER, contract.CONTROL):
            path = ROOT / relative
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            privileged = {
                str(node.slice.value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in privileged_names
            }
            self.assertEqual(privileged, set())
            self.assertNotIn("run_official_eval_local", source)
            self.assertIsNone(contract.SECRET.search(source))

    def test_protocol_is_observation_only_and_authority_never_expands(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(
            policy["only_treatment_is_content_free_first_production_normalizer_observation"]
        )
        self.assertTrue(
            policy["observer_runs_after_first_provider_response_before_sparse_fallback"]
        )
        self.assertTrue(
            policy["parent_prediction_cost_candidate_failure_and_effect_behavior_unchanged"]
        )
        self.assertFalse(
            policy[
                "observer_disposition_changes_response_fallback_prediction_candidate_routing_or_budget"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertEqual(control.EXPECTED_TESTS, 203)

    def test_resealed_row_aggregate_or_forward_tamper_fails_closed(self) -> None:
        row = self._row(malformed=False)
        changed = copy.deepcopy(row)
        changed["prediction_sha256"][contract.PRODUCTION_ARM] = "0" * 64
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)

        fallback = runner._terminal_outer_failure(
            contract.task_vector()[0], RuntimeError("synthetic"), 1.0
        )
        self.assertTrue(runner.validate_task_row(fallback)["failure_as_zero"])

    def test_build_audit_dry_run_is_valid_without_external_effect(self) -> None:
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(
            control, "_tests", return_value=fake_tests
        ), mock.patch.object(control, "_future_pristine", return_value=True):
            value = control.build_audit(now=1, require_clean=False)
        checked = control.validate_build(value)
        self.assertTrue(checked["audit_valid"])
        self.assertEqual(checked["findings"], [])
        self.assertEqual(
            checked["authorization"],
            {
                "protocol_generation_after_build_commit_push": True,
                "external_forward": False,
                "binding_successor_design": False,
                "vertical_binding_policy_change": False,
                "evaluator": False,
                "deepwidebench_dev64_exact220_or_sota": False,
            },
        )
        self.assertFalse(
            checked["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )


if __name__ == "__main__":
    unittest.main()
