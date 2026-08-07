from __future__ import annotations

import copy
import dataclasses
import hashlib
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24819_quality_first_controller import (  # noqa: E402
    CalibrationBinding,
    QualityFirstPolicy,
    decide_quality_first_state,
    run_v24819_task,
    validate_result,
)
from tests.test_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    Model,
    Search,
    limits,
    task,
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_binding(*, exchange_rate: float = 1.0) -> CalibrationBinding:
    artifact = digest(b"external-calibration-artifact")
    return CalibrationBinding(
        artifact_path="results/v24819_external_calibration_v1.json",
        declared_artifact_sha256=artifact,
        observed_artifact_sha256=artifact,
        artifact_payload_sha256=digest(b"sealed-calibration-payload"),
        calibration_task_count=128,
        terminal_utility_observed=True,
        heldout_validation_passed=True,
        external_artifact_verified_before_runtime=True,
        quality_cost_exchange_rate=exchange_rate,
    )


def policy(
    *,
    binding: CalibrationBinding | None = None,
    resource_cost: float = 1.0,
) -> QualityFirstPolicy:
    return QualityFirstPolicy(
        calibration_binding=binding or CalibrationBinding(),
        per_lookup_resource_units=resource_cost,
    )


def state_decision(
    *,
    required: tuple[str, ...],
    observed: tuple[str, ...],
    action: tuple[str, ...],
    selected_policy: QualityFirstPolicy,
    budget: int | None = None,
):
    return decide_quality_first_state(
        required_visible_cell_keys=required,
        observed_required_cell_keys=observed,
        candidate_action_cell_keys=action,
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=len(action) if budget is None else budget,
        policy=selected_policy,
    )


class EmptySuffixSearch(Search):
    """Keep the prefix identical but erase physically executed suffix records."""

    def fetch_urls(self, requests):
        batches = super().fetch_urls(requests)
        if len(self.fetch_vectors) == 3:
            for batch in batches:
                batch["results"] = []
        return batches


class V24819QualityFirstControllerTests(unittest.TestCase):
    def test_missing_required_cells_force_expansion_despite_extreme_cost(self) -> None:
        decision = state_decision(
            required=("required-a", "required-b"),
            observed=("required-a",),
            action=("required-b",),
            selected_policy=policy(
                binding=valid_binding(exchange_rate=1_000_000.0),
                resource_cost=1_000_000.0,
            ),
        )
        self.assertEqual(decision["decision"], "expand")
        self.assertEqual(decision["reason"], "mandatory_visible_cell_coverage")
        self.assertTrue(decision["mandatory_coverage_override_applied"])
        self.assertFalse(decision["quality_cost_stopping_authorized"])
        self.assertFalse(decision["quality_cost_exchange_rate_applied"])

    def test_missing_or_drifted_calibration_safe_expands_after_coverage(self) -> None:
        missing = state_decision(
            required=("required-a",),
            observed=("required-a",),
            action=("optional-check",),
            selected_policy=policy(),
        )
        good = valid_binding()
        drifted = dataclasses.replace(
            good,
            observed_artifact_sha256=digest(b"different-artifact"),
        )
        changed = state_decision(
            required=("required-a",),
            observed=("required-a",),
            action=("optional-check",),
            selected_policy=policy(binding=drifted),
        )
        for decision in (missing, changed):
            self.assertEqual(decision["decision"], "expand")
            self.assertEqual(
                decision["reason"],
                "calibration_missing_or_drifted_safe_expand",
            )
            self.assertTrue(decision["calibration_safe_expansion_applied"])
            self.assertFalse(decision["quality_cost_exchange_rate_applied"])
        self.assertIn(
            "artifact_digest_drifted",
            changed["calibration_binding_status"]["findings"],
        )

    def test_cost_stop_requires_complete_coverage_and_valid_binding(self) -> None:
        decision = state_decision(
            required=("required-a",),
            observed=("required-a",),
            action=("optional-check",),
            selected_policy=policy(
                binding=valid_binding(exchange_rate=10.0),
                resource_cost=10.0,
            ),
        )
        self.assertEqual(decision["decision"], "stop")
        self.assertEqual(
            decision["reason"], "nonpositive_calibrated_terminal_utility"
        )
        self.assertTrue(decision["quality_cost_stopping_authorized"])
        self.assertTrue(decision["quality_cost_exchange_rate_applied"])
        self.assertTrue(decision["cost_sensitive_stopping_applied"])
        self.assertEqual(decision["coverage_observation"]["missing_required_cell_count"], 0)

    def test_budget_block_is_explicit_and_never_relabelled_as_cost_stop(self) -> None:
        decision = state_decision(
            required=("required-a", "required-b"),
            observed=("required-a",),
            action=("required-b",),
            selected_policy=policy(binding=valid_binding()),
            budget=0,
        )
        self.assertEqual(decision["decision"], "stop")
        self.assertEqual(decision["reason"], "mandatory_coverage_budget_blocked")
        self.assertFalse(decision["cost_sensitive_stopping_applied"])
        self.assertFalse(decision["quality_cost_stopping_authorized"])

    def test_unactionable_required_gap_cannot_become_cost_stop(self) -> None:
        decision = state_decision(
            required=("required-a", "required-b"),
            observed=("required-a",),
            action=("optional-check",),
            selected_policy=policy(
                binding=valid_binding(exchange_rate=1_000_000.0),
                resource_cost=1_000_000.0,
            ),
        )
        self.assertEqual(decision["decision"], "stop")
        self.assertEqual(decision["reason"], "required_coverage_not_actionable")
        self.assertEqual(
            decision["coverage_observation"]["unrecoverable_missing_cell_count"],
            1,
        )
        self.assertFalse(decision["quality_cost_stopping_authorized"])
        self.assertFalse(decision["quality_cost_exchange_rate_applied"])
        self.assertFalse(decision["cost_sensitive_stopping_applied"])

    def test_worldbank_partition_is_always_mandatory_and_suffix_blind(self) -> None:
        normal = run_v24819_task(
            task(),
            model=Model(),
            search=Search(),
            limits=limits(),
            quality_first_policy=policy(
                binding=valid_binding(exchange_rate=1_000_000.0),
                resource_cost=1_000_000.0,
            ),
            monotonic=time.monotonic,
        )
        erased = run_v24819_task(
            task(),
            model=Model(),
            search=EmptySuffixSearch(),
            limits=limits(),
            quality_first_policy=policy(
                binding=valid_binding(exchange_rate=1_000_000.0),
                resource_cost=1_000_000.0,
            ),
            monotonic=time.monotonic,
        )
        self.assertEqual(
            normal["adaptive_decision"], erased["adaptive_decision"]
        )
        self.assertEqual(normal["adaptive_decision"]["decision"], "expand")
        self.assertFalse(normal["adaptive_decision"]["suffix_response_or_value_read"])
        self.assertNotEqual(
            normal["predictions"]["fixed_full_budget"],
            erased["predictions"]["fixed_full_budget"],
        )
        self.assertEqual(
            normal["predictions"]["coverage_risk_adaptive"],
            normal["predictions"]["fixed_full_budget"],
        )
        self.assertEqual(
            erased["predictions"]["coverage_risk_adaptive"],
            erased["predictions"]["fixed_full_budget"],
        )

    def test_missing_calibration_runtime_expands_and_keeps_entropy_shadow_only(self) -> None:
        value = run_v24819_task(
            task(),
            model=Model(),
            search=Search(),
            limits=limits(),
            quality_first_policy=policy(),
            monotonic=time.monotonic,
        )
        validate_result(value)
        decision = value["adaptive_decision"]
        self.assertEqual(decision["decision"], "expand")
        self.assertEqual(decision["reason"], "mandatory_visible_cell_coverage")
        self.assertEqual(decision["information_gain_feature_value"], 0.0)
        self.assertFalse(decision["entropy_assigns_signed_credit"])
        self.assertFalse(
            decision["terminal_utility_signed_credit_observed_for_this_action"]
        )
        self.assertFalse(value["receipt"]["positive_task_credit_assigned"])
        self.assertTrue(value["full_completion_check"]["passed"])

    def test_entropy_weight_and_fake_marker_binding_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "entropy"):
            dataclasses.replace(
                policy(), information_gain_feature_weight=0.01
            ).validate()
        marker = CalibrationBinding(
            artifact_path="v24805-smoke-policy-not-main-calibration",
            declared_artifact_sha256=digest(b"marker"),
            observed_artifact_sha256=digest(b"marker"),
            artifact_payload_sha256=digest(b"marker-payload"),
            calibration_task_count=1,
            terminal_utility_observed=True,
            heldout_validation_passed=True,
            external_artifact_verified_before_runtime=True,
            quality_cost_exchange_rate=1.0,
        )
        status = marker.status()
        self.assertFalse(status["valid"])
        self.assertIn("artifact_path_missing_or_invalid", status["findings"])

    def test_privileged_task_is_rejected_before_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24819_task(
                {**task(), "ground_truth": "hidden"},
                model=model,
                search=search,
                limits=limits(),
                quality_first_policy=policy(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_resealed_decision_precedence_tamper_fails(self) -> None:
        from deepwide_agent.v24804_shared_prefix_budget_ladder import payload_sha256

        value = run_v24819_task(
            task(),
            model=Model(),
            search=Search(),
            limits=limits(),
            quality_first_policy=policy(),
        )
        changed = copy.deepcopy(value)
        changed["adaptive_decision"]["decision"] = "stop"
        changed["adaptive_decision"]["reason"] = (
            "nonpositive_calibrated_terminal_utility"
        )
        changed["adaptive_decision"].pop("decision_sha256")
        changed["adaptive_decision"]["decision_sha256"] = payload_sha256(
            changed["adaptive_decision"]
        )
        changed["receipt"]["adaptive_decision_sha256"] = changed[
            "adaptive_decision"
        ]["decision_sha256"]
        changed["receipt"].pop("receipt_sha256")
        changed["receipt"]["receipt_sha256"] = payload_sha256(
            changed["receipt"]
        )
        changed.pop("result_sha256")
        changed["result_sha256"] = payload_sha256(changed)
        with self.assertRaisesRegex(ValueError, "precedence"):
            validate_result(changed)

    def test_runtime_ast_has_no_privileged_access_or_evaluator_import(self) -> None:
        from scripts.audit_v24804_shared_prefix_budget_ladder import ast_findings

        accesses, imports = ast_findings(
            Path("src/deepwide_agent/v24819_quality_first_controller.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
