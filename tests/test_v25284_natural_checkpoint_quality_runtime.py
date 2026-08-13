from __future__ import annotations

import ast
import copy
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

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25232_header_totality_shadow_runtime as fixture_parent  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as checkpoint  # noqa: E402
from deepwide_agent import v25284_natural_checkpoint_quality_runtime as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
    limits,
)


class V25284NaturalCheckpointQualityRuntimeTests(unittest.TestCase):
    @staticmethod
    def _failure_as_zero(task: dict[str, str]) -> str:
        if set(task) != {"opaque_id", "question"}:
            raise ValueError("visible boundary drifted")
        return (
            "```markdown\n| Package | Latest stable version | License | Short purpose |\n"
            "|---|---|---|---|\n"
            "| visible-a | Unknown | Unknown | Unknown |\n"
            "| visible-b | Unknown | Unknown | Unknown |\n```"
        )

    def _wiring(self, root: Path, *, inner: CompatibleModel | None = None):
        inner = inner or CompatibleModel()
        budget = cap.PhysicalEffectBudget()
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        model = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                GroundedFrontierSearch(QUESTION, phase), budget, phase=phase
            )
            for phase in fixture_parent.PHASES
        }
        return inner, budget, model, searches

    def _run(self, *, inner: CompatibleModel | None = None):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root, inner=inner)
            result = target.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
                failure_as_zero_projector=self._failure_as_zero,
            )
        return inner, budget, target.validate_result(
            result,
            task=TASK,
            failure_as_zero_projector=self._failure_as_zero,
        )

    def test_clean_parent_is_identity_pair_with_one_real_forward(self) -> None:
        inner, budget, result = self._run()
        receipt = result["content_free_quality_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(
            result["arms"][target.CONTROL_ARM],
            result["arms"][target.CANDIDATE_ARM],
        )
        self.assertEqual(receipt["outcome_reason"], "clean_identity")
        self.assertFalse(receipt["natural_postcheckpoint_recovery_present"])
        self.assertTrue(receipt["control_and_candidate_prediction_equal"])
        self.assertEqual(
            result["parent_stage_receipt"]["outer_physical_budget_receipt"],
            budget.receipt(),
        )

    def test_natural_postcheckpoint_failure_projects_legacy_zero_vs_checkpoint(self) -> None:
        with mock.patch.object(
            checkpoint,
            "_build_result",
            side_effect=ValueError("hidden natural envelope detail"),
        ):
            inner, budget, result = self._run()
        receipt = result["content_free_quality_receipt"]
        control = result["arms"][target.CONTROL_ARM]
        candidate = result["arms"][target.CANDIDATE_ARM]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(
            receipt["outcome_reason"], "natural_postcheckpoint_recovery"
        )
        self.assertTrue(receipt["natural_postcheckpoint_recovery_present"])
        self.assertTrue(receipt["legacy_failure_as_zero_counterfactual_active"])
        self.assertTrue(receipt["candidate_preserves_trusted_checkpoint"])
        self.assertTrue(receipt["control_and_candidate_prediction_changed"])
        self.assertEqual(control["prediction_kind"], "visible_fallback")
        self.assertEqual(candidate["prediction_kind"], "model_generated")
        self.assertEqual(
            candidate["prediction"], result["parent_result"]["prediction"]
        )
        self.assertEqual(
            result["parent_stage_receipt"]["outer_physical_budget_receipt"],
            budget.receipt(),
        )
        self.assertNotIn("hidden natural envelope detail", str(result))
        for field in (
            "candidate_additional_query_count",
            "candidate_additional_fetch_count",
            "candidate_additional_model_forward_count",
            "candidate_additional_system_total_tokens",
            "positive_signed_credit_count",
        ):
            self.assertEqual(receipt[field], 0)

    def test_natural_parent_validation_failure_uses_regular_recovery_result(self) -> None:
        original = sparse.parent.validate_result
        calls = 0

        def fail_first(value):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ValueError("hidden natural parent validation detail")
            return original(value)

        with mock.patch.object(
            sparse.parent, "validate_result", side_effect=fail_first
        ):
            inner, _budget, result = self._run()
        receipt = result["content_free_quality_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["parent_result"]["role"], checkpoint.ROLE)
        self.assertEqual(
            receipt["outcome_reason"], "natural_postcheckpoint_recovery"
        )
        self.assertEqual(
            receipt["observed_failure_stages"],
            ["paired_parent_run_and_validate"],
        )
        self.assertTrue(receipt["control_and_candidate_prediction_changed"])
        self.assertNotIn("hidden natural parent validation detail", str(result))

    def test_precheckpoint_failure_remains_identity_failure_as_zero(self) -> None:
        with mock.patch.object(
            sparse.parent,
            "run_paired_task",
            side_effect=ValueError("hidden precheckpoint detail"),
        ):
            inner, _budget, result = self._run()
        receipt = result["content_free_quality_receipt"]
        self.assertEqual(inner.logical_calls, 0)
        self.assertEqual(
            receipt["outcome_reason"], "precheckpoint_visible_fallback_identity"
        )
        self.assertFalse(receipt["trusted_checkpoint_present"])
        self.assertEqual(
            result["arms"][target.CONTROL_ARM],
            result["arms"][target.CANDIDATE_ARM],
        )
        self.assertNotIn("hidden precheckpoint detail", str(result))

    def test_injected_fault_marker_is_rejected_even_when_nested_seals_match(self) -> None:
        with mock.patch.object(
            checkpoint, "_build_result", side_effect=ValueError("natural")
        ):
            _inner, _budget, result = self._run()
        changed = copy.deepcopy(result)
        parent_result = changed["parent_result"]
        stage = changed["parent_stage_receipt"]
        failed_stage = parent_result["recovered_failure_stages"][0]
        parent_result["recovered_failure_types"][failed_stage] = (
            target.INJECTED_FAILURE_TYPE
        )
        parent_result.pop("result_payload_sha256")
        parent_result["result_payload_sha256"] = payload_sha256(parent_result)
        changed["parent_result_payload_sha256"] = parent_result[
            "result_payload_sha256"
        ]
        stage["stage_failure_types"][failed_stage] = target.INJECTED_FAILURE_TYPE
        stage.pop("receipt_payload_sha256")
        stage["receipt_payload_sha256"] = payload_sha256(stage)
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(
                changed,
                task=TASK,
                failure_as_zero_projector=self._failure_as_zero,
            )

    def test_resealed_result_stage_binding_mismatch_fails(self) -> None:
        _inner, _budget, result = self._run()
        for kind in ("disposition", "checkpoint", "parent", "failure_count"):
            changed = copy.deepcopy(result)
            stage = changed["parent_stage_receipt"]
            if kind == "disposition":
                stage["recovery_disposition"] = (
                    "validated_production_preserved_after_post_checkpoint_failure"
                )
            elif kind == "checkpoint":
                stage["checkpoint_kind"] = "deterministic_fallback"
            elif kind == "parent":
                stage["parent_result_retained"] = False
            else:
                stage["stage_failure_types"]["result_envelope_validate"] = (
                    "ValueError"
                )
                stage["stage_completed_counts"]["result_envelope_validate"] = 0
                stage["failure_count"] = 1
            stage.pop("receipt_payload_sha256")
            stage["receipt_payload_sha256"] = payload_sha256(stage)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(
                    changed,
                    task=TASK,
                    failure_as_zero_projector=self._failure_as_zero,
                )

    def test_resealed_regular_role_cannot_claim_natural_recovery(self) -> None:
        with mock.patch.object(
            checkpoint, "_build_result", side_effect=ValueError("natural")
        ):
            _inner, _budget, result = self._run()
        changed = copy.deepcopy(result)
        parent_result = changed["parent_result"]
        parent_result["role"] = checkpoint.ROLE
        parent_result.pop("recovered_failure_stages")
        parent_result.pop("recovered_failure_types")
        parent_result.pop(
            "recovery_envelope_is_independent_of_failed_parent_or_primary_envelope"
        )
        parent_result["parent_result"] = None
        parent_result["parent_result_payload_sha256"] = None
        parent_result.pop("result_payload_sha256")
        parent_result["result_payload_sha256"] = payload_sha256(parent_result)
        changed["parent_result_payload_sha256"] = parent_result[
            "result_payload_sha256"
        ]
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(
                changed,
                task=TASK,
                failure_as_zero_projector=self._failure_as_zero,
            )

    def test_resealed_arm_task_receipt_or_hidden_tamper_fails(self) -> None:
        _inner, _budget, result = self._run()
        for kind in ("arm", "task", "credit", "effect", "hidden"):
            changed = copy.deepcopy(result)
            task = TASK
            if kind == "arm":
                changed["arms"][target.CANDIDATE_ARM]["prediction"] += "x"
            elif kind == "task":
                task = {**TASK, "question": TASK["question"] + " changed"}
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            elif kind == "effect":
                receipt = changed["content_free_quality_receipt"]
                receipt["candidate_additional_model_forward_count"] = 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            else:
                changed["content_free_quality_receipt"]["hidden"] = True
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(
                    changed,
                    task=task,
                    failure_as_zero_projector=self._failure_as_zero,
                )

    def test_failure_as_zero_projector_is_recomputed_and_bound(self) -> None:
        with mock.patch.object(
            checkpoint, "_build_result", side_effect=ValueError("natural")
        ):
            _inner, _budget, result = self._run()

        def different_projector(task: dict[str, str]) -> str:
            del task
            return "| Different |\n|---|\n| Unknown |"

        with self.assertRaises(ValueError):
            target.validate_result(
                result,
                task=TASK,
                failure_as_zero_projector=different_projector,
            )

        for bad in (
            lambda _task: "",
            lambda _task: None,
        ):
            with self.subTest(projector=bad), self.assertRaises(ValueError):
                target.validate_result(
                    result,
                    task=TASK,
                    failure_as_zero_projector=bad,
                )

    def test_existing_external_projector_matches_visible_two_row_contract(self) -> None:
        from deepwide_agent import (  # noqa: PLC0415
            v25280_paired_checkpoint_reliability_external_contract as contract,
        )
        from scripts import (  # noqa: PLC0415
            run_v25280_paired_checkpoint_reliability_external as runner,
        )

        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 20)
        for task in tasks:
            visible = {
                "opaque_id": task["opaque_id"],
                "question": task["question"],
            }
            projected = runner._fallback_table(visible)
            packages = contract.packages_from_question(visible["question"])
            self.assertEqual(len(packages), 2)
            self.assertEqual(
                projected.count("| Unknown | Unknown | Unknown |"), 2
            )
            for package in packages:
                self.assertIn(
                    f"| {package} | Unknown | Unknown | Unknown |", projected
                )

    def test_source_is_label_blind_and_has_no_effect_or_evaluator_capability(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25284_natural_checkpoint_quality_runtime.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
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
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "urllib",
            "openai",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        for forbidden in (
            "official_eval",
            "run_official",
            "api_key",
            "os.environ",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
