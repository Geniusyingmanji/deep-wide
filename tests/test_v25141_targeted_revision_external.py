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
from deepwide_agent import v25141_targeted_revision_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import run_v25141_targeted_revision_external as runner  # noqa: E402
from scripts import control_v25141_targeted_revision_external as control  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
)


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


class TargetedRevisionExternalTests(unittest.TestCase):
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

    def test_gate_requires_targeted_projection_reach_and_attribution(self) -> None:
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_verified_gain_tasks"], 4)
        self.assertEqual(gate["maximum_verified_gain_tasks"], 16)
        self.assertEqual(gate["minimum_attributable_prediction_changed_tasks"], 3)
        self.assertEqual(gate["minimum_targeted_projection_applied_tasks"], 3)
        self.assertEqual(gate["minimum_applied_changed_cells"], 3)
        self.assertEqual(gate["maximum_sparse_model_forwards_total"], 76)
        self.assertEqual(gate["minimum_model_forwards_saved_vs_dense"], 4)
        quality = contract.quality_gate()
        self.assertTrue(quality["candidate_exact_strict_gain"])
        self.assertTrue(
            quality["candidate_entity_row_item_column_composite_nonregression"]
        )

    def test_synthetic_targeted_task_row_and_aggregate_validate(self) -> None:
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
        sparse = checked["parent_result"]["content_free_receipt"]
        self.assertEqual(sparse["provider_forward_count"], 3)
        self.assertFalse(sparse["verified_source_identity_field_gain"])
        self.assertEqual(receipt["targeted_revision_entry_count"], 0)
        self.assertEqual(
            checked["predictions"][contract.PRODUCTION_ARM],
            checked["predictions"][contract.TARGETED_FINAL_ARM],
        )

    def test_synthetic_positive_gain_cross_binds_sparse_and_targeted_effects(self) -> None:
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
                    task["question"], phase, field_page=True
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
        targeted = checked["content_free_receipt"]
        sparse = checked["parent_result"]["content_free_receipt"]
        effects = checked["actual_effect_snapshot"]
        self.assertTrue(sparse["verified_source_identity_field_gain"])
        self.assertEqual(sparse["provider_forward_count"], 4)
        self.assertEqual(effects["model_logical_requests"], 4)
        self.assertTrue(targeted["targeted_prompt_built"])
        self.assertTrue(targeted["production_table_conditioned"])
        self.assertTrue(targeted["projection_valid"])
        self.assertTrue(targeted["projection_applied"])
        self.assertEqual(targeted["applied_changed_cell_count"], 1)
        self.assertNotEqual(
            checked["predictions"][contract.PRODUCTION_ARM],
            checked["predictions"][contract.TARGETED_FINAL_ARM],
        )
        tampered = copy.deepcopy(checked)
        tampered["failure_types"]["plan"] = "ValueError"
        tampered = contract.seal(tampered, "result_payload_sha256")
        with self.assertRaises(RuntimeError):
            runner.validate_task_row(tampered)

    def test_mechanism_decision_rejects_dense_or_unattributable_rows(self) -> None:
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
            "targeted_prompt_built_tasks": 9,
            "targeted_revision_entry_tasks": 9,
            "targeted_underlying_provider_forward_tasks": 9,
            "production_table_conditioned_tasks": 9,
            "targeted_projection_valid_tasks": 9,
            "targeted_projection_applied_tasks": 3,
            "targeted_applied_changed_cells": 3,
            "targeted_rejected_changed_cells": 0,
            "targeted_conflicting_changed_cells": 0,
            "targeted_context_cap_violation_tasks": 0,
            "targeted_verified_delta_violation_tasks": 0,
            "targeted_projection_failure_tasks": 0,
            "targeted_provider_failure_tasks": 0,
            "targeted_parent_post_effect_failure_tasks": 0,
            "prediction_changed_tasks": 3,
            "attributable_prediction_changed_tasks": 3,
            "unattributable_prediction_changed_tasks": 0,
            "revision_failure_tasks": 0,
            "post_effect_failure_tasks": 0,
            "parent_prediction_loss_tasks": 0,
            "content_free_receipt_valid_tasks": 20,
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
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for name, value in (
            ("physical_model_forwards", 80),
            ("unattributable_prediction_changed_tasks", 1),
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] = value
            self.assertFalse(
                runner.mechanism_decision(changed)["mechanism_gate_passed"]
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
