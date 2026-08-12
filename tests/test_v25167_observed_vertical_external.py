from __future__ import annotations

import ast
import copy
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
from deepwide_agent import v25167_observed_vertical_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import run_v25167_observed_vertical_external as runner  # noqa: E402
from scripts import control_v25167_observed_vertical_external as control  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
)
from test_v25151_generic_record_quote_candidate_runtime import CandidateModel  # noqa: E402


class AccountingSyntheticSearch(GroundedFrontierSearch):
    def __init__(self, *args, vertical_page: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._vertical_page = vertical_page
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
        output = super().fetch_urls(values)
        if self._vertical_page and self._phase == contract.runtime.SECOND_PHASE:
            for response in output:
                for result in response["results"]:
                    if "iana.org/domains/root/db/records/in.html" in result["url"]:
                        result["raw_content"] = (
                            "Domain | .in\n"
                            "Type | country-code\n"
                            "TLD Manager | 999"
                        )
        return output


class ObservedVerticalExternalTests(unittest.TestCase):
    def test_fresh_population_schema_and_history_literal_zero(self) -> None:
        tasks = contract.task_vector()
        selection = contract.validate_population_selection_audit(
            ROOT, tracked=False
        )
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
        self.assertTrue(
            all(
                "https://" not in row["question"]
                and "<PACKAGE>" not in row["question"]
                for row in tasks
            )
        )
        for clue in contract.CLUES:
            observed = subprocess.run(
                [
                    "git",
                    "grep",
                    "-F",
                    "-i",
                    "--",
                    clue,
                    contract.FRESHNESS_PARENT_COMMIT,
                    "--",
                    ".",
                    ":(exclude)plan.md",
                    ":(exclude)survey.md",
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(observed.returncode, 1)
            self.assertEqual(observed.stdout, "")

    def test_gate_requires_reliable_disposition_localization(self) -> None:
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_verified_gain_tasks"], 4)
        self.assertEqual(gate["maximum_verified_gain_tasks"], 16)
        self.assertEqual(gate["minimum_observer_completed_tasks"], 4)
        self.assertEqual(gate["maximum_observer_failure_tasks"], 0)
        self.assertEqual(gate["minimum_observed_page_count"], 4)
        self.assertEqual(gate["minimum_vertical_block_tasks"], 2)
        self.assertEqual(gate["minimum_vertical_blocks"], 3)
        self.assertEqual(gate["minimum_nonzero_disposition_buckets"], 1)
        self.assertEqual(gate["minimum_rejected_vertical_blocks"], 1)
        self.assertEqual(gate["maximum_disposition_accounting_error"], 0)
        self.assertEqual(gate["maximum_parent_behavior_drift_tasks"], 0)
        self.assertEqual(gate["maximum_positive_signed_credit_count"], 0)
        self.assertEqual(gate["maximum_sparse_model_forwards_total"], 76)
        self.assertEqual(gate["minimum_model_forwards_saved_vs_dense"], 4)
        quality = contract.quality_gate()
        self.assertFalse(quality["quality_evaluator_authorized"])
        self.assertTrue(quality["localization_gate_cannot_establish_outer_utility"])

    def test_synthetic_no_gain_task_row_and_aggregate_validate(self) -> None:
        task = {
            "opaque_id": contract.task_vector()[0]["opaque_id"],
            "question": (
                "Identify the country matching this public clue: capital New Delhi "
                "and currency INR. Resolve it from public pages, then use the visible "
                "IANA Root Zone Database authority. Return one table. Columns exactly: "
                "Domain | Type | TLD Manager. Preserve spelling."
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            class SyntheticModel(CompatibleModel):
                def complete(
                    self,
                    system,
                    user,
                    *,
                    max_output_tokens,
                    json_mode=False,
                ):
                    value = super().complete(
                        system,
                        user,
                        max_output_tokens=max_output_tokens,
                        json_mode=json_mode,
                    )
                    self.calls = self.requests
                    return value

            inner = SyntheticModel()
            model = runner._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: AccountingSyntheticSearch(
                    task["question"], phase, field_page=False
                )
                for phase in contract.runtime.PHASES
            }
            value = contract.runtime.run_task(
                task,
                model=model,
                searches=searches,
                limits=ScoreFirstLimits(**contract.LIMITS),
            )
            row = runner._from_runtime(
                task,
                value,
                1.0,
                runner._health(),
                runner._actual_effect_snapshot(model, searches),
            )
        checked = runner.validate_task_row(row)
        receipt = checked["content_free_receipt"]
        frozen = checked["parent_result"]["content_free_receipt"]
        sparse = checked["parent_result"]["parent_result"]["content_free_receipt"]
        self.assertEqual(sparse["provider_forward_count"], 3)
        self.assertFalse(sparse["verified_source_identity_field_gain"])
        self.assertEqual(frozen["candidate_revision_entry_count"], 0)
        self.assertEqual(frozen["available_candidate_count"], 0)
        self.assertEqual(frozen["selected_candidate_count"], 0)
        self.assertEqual(receipt["disposition_observer_entry_count"], 0)
        self.assertEqual(receipt["disposition_observer_completed_count"], 0)
        self.assertIsNone(receipt["disposition_observation"])
        self.assertEqual(
            checked["predictions"][contract.PRODUCTION_ARM],
            checked["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        )

    def test_synthetic_positive_gain_cross_binds_sparse_and_candidate_effects(self) -> None:
        task = {
            "opaque_id": contract.task_vector()[0]["opaque_id"],
            "question": (
                "Identify the country matching this public clue: capital New Delhi "
                "and currency INR. Resolve it from public pages, then use the visible "
                "IANA Root Zone Database authority. Return one table. Columns exactly: "
                "Domain | Type | TLD Manager. Preserve spelling."
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")

            class SyntheticModel(CandidateModel):
                def complete(self, system, user, *, max_output_tokens, json_mode=False):
                    value = super().complete(
                        system,
                        user,
                        max_output_tokens=max_output_tokens,
                        json_mode=json_mode,
                    )
                    self.calls = self.requests
                    return value

            inner = SyntheticModel()
            model = runner._EffectAccountingModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: AccountingSyntheticSearch(
                    task["question"],
                    phase,
                    field_page=False,
                    vertical_page=True,
                )
                for phase in contract.runtime.PHASES
            }
            value = contract.runtime.run_task(
                task,
                model=model,
                searches=searches,
                limits=ScoreFirstLimits(**contract.LIMITS),
            )
            row = runner._from_runtime(
                task,
                value,
                1.0,
                runner._health(),
                runner._actual_effect_snapshot(model, searches),
            )
        checked = runner.validate_task_row(row)
        observed = checked["content_free_receipt"]
        candidate = checked["parent_result"]["content_free_receipt"]
        sparse = checked["parent_result"]["parent_result"]["content_free_receipt"]
        effects = checked["actual_effect_snapshot"]
        self.assertTrue(sparse["verified_source_identity_field_gain"])
        self.assertEqual(sparse["provider_forward_count"], 4)
        self.assertEqual(effects["model_logical_requests"], 4)
        self.assertTrue(candidate["selector_prompt_built"])
        self.assertTrue(candidate["production_table_conditioned"])
        self.assertEqual(candidate["vertical_pipe_block_count"], 1)
        self.assertEqual(candidate["vertical_identity_bound_block_count"], 1)
        self.assertEqual(
            candidate["vertical_key_value_record_observation_count"], 1
        )
        self.assertGreaterEqual(candidate["available_candidate_count"], 1)
        self.assertGreaterEqual(candidate["supplied_candidate_count"], 1)
        self.assertEqual(candidate["selected_candidate_count"], 1)
        self.assertTrue(candidate["selection_response_strict_json"])
        self.assertTrue(candidate["candidate_projection_valid"])
        self.assertEqual(candidate["applied_edit_count"], 1)
        self.assertEqual(candidate["rejected_selected_edit_count"], 0)
        self.assertEqual(observed["disposition_observer_entry_count"], 1)
        self.assertEqual(observed["disposition_observer_completed_count"], 1)
        self.assertFalse(observed["disposition_observer_failure_present"])
        self.assertEqual(observed["verified_delta_computation_count"], 1)
        self.assertEqual(observed["verified_delta_cache_reuse_count"], 1)
        self.assertEqual(
            observed["disposition_observation"]["disposition_counts"][
                "identity_bound_candidate_ready"
            ],
            1,
        )
        self.assertNotEqual(
            checked["predictions"][contract.PRODUCTION_ARM],
            checked["predictions"][contract.DETERMINISTIC_FINAL_ARM],
        )
        tampered = copy.deepcopy(checked)
        tampered["failure_types"]["plan"] = "ValueError"
        tampered = contract.seal(tampered, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(tampered)

    def test_localization_decision_rejects_missing_reach_parity_or_reliability(self) -> None:
        aggregate = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "production_model_generated_tasks": 20,
            "production_fallback_tasks": 0,
            "verified_gain_tasks": 9,
            "revision_provider_forward_tasks": 9,
            "revision_provider_valid_tasks": 9,
            "identity_replay_tasks": 11,
            "candidate_revision_entry_tasks": 9,
            "candidate_underlying_provider_forward_tasks": 9,
            "candidate_selector_prompt_built_tasks": 9,
            "production_table_conditioned_tasks": 9,
            "candidate_selection_strict_json_tasks": 9,
            "candidate_projection_valid_tasks": 9,
            "bound_json_record_observations": 0,
            "pipe_table_observations": 0,
            "flat_json_object_observations": 0,
            "inline_labelled_record_observations": 0,
            "multiline_labelled_record_observations": 0,
            "heading_labelled_record_observations": 0,
            "vertical_candidate_observations": 3,
            "vertical_pipe_blocks": 3,
            "vertical_identity_bound_tasks": 2,
            "vertical_identity_bound_blocks": 2,
            "vertical_ambiguous_pages": 0,
            "vertical_candidate_available_tasks": 3,
            "vertical_candidate_selected_tasks": 3,
            "vertical_reverified_applied_tasks": 3,
            "vertical_attributable_prediction_changed_tasks": 3,
            "raw_candidate_observations": 3,
            "verifier_admissible_candidates": 3,
            "conflicting_candidates": 0,
            "duplicate_candidates": 0,
            "truncated_candidates": 0,
            "candidate_available_tasks": 3,
            "available_candidates": 3,
            "candidate_supplied_tasks": 3,
            "supplied_candidates": 3,
            "candidate_selected_tasks": 3,
            "selected_candidates": 3,
            "reverified_applied_tasks": 3,
            "applied_edits": 3,
            "rejected_selected_edits": 0,
            "candidate_context_cap_violation_tasks": 0,
            "candidate_verified_delta_violation_tasks": 0,
            "candidate_projection_failure_tasks": 0,
            "candidate_provider_failure_tasks": 0,
            "candidate_parent_post_effect_failure_tasks": 0,
            "prediction_changed_tasks": 3,
            "attributable_prediction_changed_tasks": 3,
            "unattributable_prediction_changed_tasks": 0,
            "positive_signed_credit_count": 0,
            "revision_failure_tasks": 0,
            "post_effect_failure_tasks": 0,
            "parent_prediction_loss_tasks": 0,
            "content_free_receipt_valid_tasks": 20,
            "observer_entry_tasks": 9,
            "observer_completed_tasks": 9,
            "observer_failure_tasks": 0,
            "verified_delta_computations": 9,
            "verified_delta_cache_reuses": 9,
            "observed_page_count": 9,
            "vertical_block_tasks": 3,
            "observed_vertical_blocks": 3,
            "observed_identity_bound_blocks": 2,
            "observed_ambiguous_pages": 0,
            "observed_frozen_vertical_candidates": 3,
            "disposition_counts": {
                "empty_or_duplicate_normalized_key_reject": 0,
                "mapped_field_unsafe_or_unknown_value_reject": 0,
                "no_visible_schema_key_reject": 0,
                "missing_primary_key_row_reject": 1,
                "multiple_primary_key_rows_reject": 0,
                "primary_identity_not_unique_production_row_reject": 0,
                "identity_bound_without_nonkey_visible_field": 0,
                "identity_bound_quote_span_reject": 0,
                "identity_bound_without_changed_safe_candidate": 0,
                "identity_bound_candidate_ready": 2,
            },
            "nonzero_disposition_buckets": 2,
            "rejected_vertical_blocks": 1,
            "disposition_accounting_error": 0,
            "parent_behavior_drift_tasks": 0,
            "physical_queries": 80,
            "physical_fetches": 200,
            "physical_model_forwards": 69,
            "dense_reference_model_forwards": 80,
            "model_forwards_saved_vs_dense": 11,
            "model_provider_requests": 69,
            "model_provider_attempts": 69,
            "system_total_tokens": 1,
            "observed_all_task_model_logical_requests": 69,
            "observed_all_task_logical_queries": 80,
            "observed_all_task_fetch_requests": 200,
            "outer_or_accounting_failure_tasks": 0,
            "terminal_transport_timeout_helper_or_model_hard_failures": 0,
            "batch_wall_seconds": 1.0,
            "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        decision = runner.mechanism_decision(aggregate)
        self.assertTrue(decision["localization_gate_passed"])
        self.assertTrue(decision["binding_successor_design"])
        self.assertFalse(
            decision["postfreeze_external_evaluator_implementation_and_protocol"]
        )
        for name, value in (
            ("physical_model_forwards", 80),
            ("observer_failure_tasks", 1),
            ("vertical_block_tasks", 1),
            ("disposition_accounting_error", 1),
            ("parent_behavior_drift_tasks", 1),
            ("positive_signed_credit_count", 1),
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] = value
            self.assertFalse(
                runner.mechanism_decision(changed)["localization_gate_passed"]
            )
        changed = copy.deepcopy(aggregate)
        changed["disposition_counts"]["missing_primary_key_row_reject"] = 0
        changed["disposition_counts"][
            "identity_bound_without_nonkey_visible_field"
        ] = 1
        self.assertFalse(
            runner.mechanism_decision(changed)["localization_gate_passed"]
        )

    def test_contract_and_runner_are_label_blind_and_evaluator_free(self) -> None:
        for relative in (contract.CONTRACT, contract.RUNNER):
            path = ROOT / relative
            tree = ast.parse(path.read_text(encoding="utf-8"))
            privileged: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(
                    node.slice, ast.Constant
                ):
                    if node.slice.value in {
                        "category",
                        "question_type",
                        "task_category",
                        "split",
                        "ground_truth",
                        "gold",
                        "answer_key",
                        "score",
                        "reward",
                    }:
                        privileged.append(str(node.slice.value))
            self.assertEqual(privileged, [])
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("run_official_eval_local", text)
            self.assertIsNone(contract.SECRET.search(text))

    def test_protocol_treatment_is_behavior_preserving_observation_only(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(
            policy[
                "candidates_cover_bound_flat_json_pipe_inline_multiline_heading_and_vertical_key_value_records"
            ]
        )
        self.assertTrue(
            policy[
                "vertical_blocks_require_unique_primary_identity_and_unique_visible_keys"
            ]
        )
        self.assertTrue(
            policy[
                "vertical_quotes_are_same_page_unique_bounded_identity_to_field_spans"
            ]
        )
        self.assertTrue(
            policy[
                "every_candidate_is_preverified_and_selected_edit_reverified"
            ]
        )
        self.assertTrue(policy["model_only_selects_candidate_ids_or_abstains"])
        self.assertTrue(policy["observer_and_parent_share_one_verified_delta_cache"])
        self.assertTrue(policy["observer_failure_isolated_and_parent_continues"])
        self.assertFalse(
            policy[
                "observer_reason_buckets_change_admission_routing_prediction_or_budget"
            ]
        )
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit"])
        self.assertEqual(control.EXPECTED_TESTS, 186)

    def test_resealed_row_or_forward_tamper_fails_closed(self) -> None:
        fallback = runner._fallback_table()
        row = runner._terminal_outer_failure(
            contract.task_vector()[0], RuntimeError("synthetic"), 1.0
        )
        checked = runner.validate_task_row(row)
        self.assertEqual(
            checked["predictions"],
            {arm: fallback for arm in contract.ARMS},
        )
        changed = copy.deepcopy(checked)
        changed["prediction_sha256"][contract.PRODUCTION_ARM] = "0" * 64
        changed = contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(changed)


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
        self.assertFalse(checked["authorization"]["external_forward"])
        self.assertFalse(
            checked["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )


if __name__ == "__main__":
    unittest.main()
