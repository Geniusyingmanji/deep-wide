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
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25232_header_totality_shadow_runtime as fixture_parent  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25265_production_only_totality_runtime as control  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as target  # noqa: E402
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


class V25271ValidatedProductionCheckpointRuntimeTests(unittest.TestCase):
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

    def _run_target(self, *, inner: CompatibleModel | None = None):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root, inner=inner)
            result, stage = target.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return (
            inner,
            target.validate_result(result),
            target.validate_stage_receipt(stage),
        )

    def _run_control(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root)
            result, stage = control.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, control.validate_result(result), control.validate_stage_receipt(stage)

    def test_normal_path_prediction_cost_and_provider_effect_match_parent(self) -> None:
        control_inner, control_result, _control_stage = self._run_control()
        inner, result, stage = self._run_target()
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, control_inner.logical_calls)
        self.assertEqual(result["prediction"], control_result["prediction"])
        self.assertEqual(result["prediction_kind"], control_result["prediction_kind"])
        self.assertEqual(result["cost"], control_result["cost"])
        self.assertEqual(receipt["provider_forward_count"], 3)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertEqual(
            receipt["physical_fetch_count"],
            control_result["content_free_receipt"]["physical_fetch_count"],
        )
        self.assertEqual(receipt["physical_model_forward_count"], 3)
        self.assertEqual(receipt["recovery_disposition"], "clean_validated_production")
        self.assertEqual(stage["failure_count"], 0)
        self.assertEqual(stage["stage_entered_counts"], {name: 1 for name in target.STAGES})
        self.assertEqual(stage["stage_completed_counts"], {name: 1 for name in target.STAGES})

    def test_post_checkpoint_parent_validation_failure_preserves_table(self) -> None:
        baseline_inner, baseline, _baseline_stage = self._run_target()

        def fail_after_run(value):
            del value
            raise ValueError("hidden parent binding detail")

        with mock.patch.object(sparse.parent, "validate_result", side_effect=fail_after_run):
            inner, result, stage = self._run_target()
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertIsNotNone(result["production_checkpoint"])
        self.assertIsNone(result["parent_result"])
        self.assertEqual(
            result["content_free_receipt"]["recovery_disposition"],
            "validated_production_preserved_after_post_checkpoint_failure",
        )
        self.assertEqual(
            stage["stage_failure_types"]["paired_parent_run_and_validate"],
            "ValueError",
        )
        self.assertNotIn("hidden parent binding detail", str(result))
        self.assertNotIn("hidden parent binding detail", str(stage))

    def test_pre_checkpoint_failure_uses_visible_schema_fallback(self) -> None:
        with mock.patch.object(
            sparse.parent, "run_paired_task", side_effect=ValueError("hidden precheckpoint")
        ):
            inner, result, stage = self._run_target()
        self.assertEqual(inner.logical_calls, 0)
        self.assertEqual(result["prediction_kind"], "visible_fallback")
        self.assertIsNone(result["production_checkpoint"])
        self.assertIsNone(result["parent_result"])
        self.assertIn("| Domain | Type | TLD Manager |", result["prediction"])
        self.assertIn("| Unknown | Unknown | Unknown |", result["prediction"])
        self.assertEqual(
            result["content_free_receipt"]["recovery_disposition"],
            "visible_fallback_before_checkpoint",
        )
        self.assertEqual(
            stage["stage_failure_types"]["paired_parent_run_and_validate"],
            "ValueError",
        )
        self.assertNotIn("hidden precheckpoint", str(result))

    def test_production_model_failure_checkpoints_deterministic_fallback(self) -> None:
        inner = CompatibleModel()
        original = inner.complete

        def fail_third(system, user, *, max_output_tokens, json_mode=False):
            if inner.logical_calls == 2:
                from deepwide_agent.clients import ModelRequestError

                inner.logical_calls += 1
                inner.requests += 1
                inner.attempts += 1
                raise ModelRequestError("hidden production transport")
            return original(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )

        inner.complete = fail_third
        _inner, result, stage = self._run_target(inner=inner)
        checkpoint = result["production_checkpoint"]
        self.assertEqual(result["prediction_kind"], "fallback")
        self.assertEqual(checkpoint["checkpoint_kind"], "deterministic_fallback")
        self.assertEqual(checkpoint["production_failure_type"], "ModelRequestError")
        self.assertEqual(
            result["content_free_receipt"]["recovery_disposition"],
            "clean_deterministic_fallback",
        )
        self.assertEqual(stage["failure_count"], 0)
        self.assertNotIn("hidden production transport", str(result))

    def test_primary_envelope_build_failure_uses_independent_recovery_envelope(self) -> None:
        _baseline_inner, baseline, _baseline_stage = self._run_target()
        with mock.patch.object(
            target, "_build_result", side_effect=ValueError("hidden build detail")
        ):
            inner, result, stage = self._run_target()
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["role"], target.RECOVERY_ROLE)
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertIsNone(result["parent_result"])
        self.assertEqual(
            result["recovered_failure_stages"], ["result_envelope_build"]
        )
        self.assertEqual(
            result["recovered_failure_types"], {"result_envelope_build": "ValueError"}
        )
        self.assertEqual(
            result["content_free_receipt"]["recovery_disposition"],
            "validated_production_preserved_after_post_checkpoint_failure",
        )
        self.assertEqual(
            stage["stage_failure_types"]["result_envelope_build"], "ValueError"
        )
        self.assertNotIn("hidden build detail", str(result))

    def test_primary_envelope_validation_failure_uses_independent_recovery_envelope(self) -> None:
        _baseline_inner, baseline, _baseline_stage = self._run_target()
        original = target.validate_result

        def fail_primary(value):
            if value.get("role") == target.ROLE:
                raise ValueError("hidden validation detail")
            return original(value)

        with mock.patch.object(target, "validate_result", side_effect=fail_primary):
            inner, result, stage = self._run_target()
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["role"], target.RECOVERY_ROLE)
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertEqual(
            result["recovered_failure_stages"], ["result_envelope_validate"]
        )
        self.assertEqual(
            stage["stage_failure_types"]["result_envelope_validate"], "ValueError"
        )
        self.assertNotIn("hidden validation detail", str(result))

    def test_untrusted_checkpoint_fails_closed_with_finite_stage_receipt(self) -> None:
        with mock.patch.object(
            target, "validate_checkpoint", side_effect=ValueError("hidden checkpoint detail")
        ):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
                root = Path(raw)
                _inner, budget, model, searches = self._wiring(root)
                with self.assertRaises(target.ProductionCheckpointStageError) as caught:
                    target.run_task(
                        TASK,
                        model=model,
                        searches=searches,
                        limits=limits(),
                        budget=budget,
                        monotonic=time.monotonic,
                    )
        receipt = caught.exception.stage_receipt
        self.assertEqual(
            receipt["stage_failure_types"]["production_checkpoint_select"],
            "ValueError",
        )
        self.assertEqual(receipt["recovery_disposition"], "untrusted_checkpoint_rejected")
        self.assertIsNone(receipt["checkpoint_kind"])
        self.assertNotIn("hidden checkpoint detail", str(receipt))

    def test_checkpoint_receipt_and_result_tamper_fail_closed(self) -> None:
        _inner, result, stage = self._run_target()
        for kind in ("checkpoint", "receipt", "result", "stage", "credit"):
            changed = copy.deepcopy(result)
            if kind == "checkpoint":
                checkpoint = changed["production_checkpoint"]
                checkpoint["prediction"] += "x"
                checkpoint.pop("checkpoint_payload_sha256")
                checkpoint["checkpoint_payload_sha256"] = payload_sha256(checkpoint)
                changed["production_checkpoint_payload_sha256"] = checkpoint[
                    "checkpoint_payload_sha256"
                ]
            elif kind == "receipt":
                receipt = changed["content_free_receipt"]
                receipt["parent_result_retained"] = False
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            elif kind == "result":
                changed["prediction_kind"] = "fallback"
            elif kind == "credit":
                receipt = changed["content_free_receipt"]
                receipt["positive_signed_credit_count"] = 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            else:
                stage_changed = copy.deepcopy(stage)
                stage_changed["stage_completed_counts"]["result_envelope_validate"] = 0
                stage_changed.pop("receipt_payload_sha256")
                stage_changed["receipt_payload_sha256"] = payload_sha256(stage_changed)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(stage_changed)
                continue
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_source_is_label_blind_and_has_no_effect_or_evaluator_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25271_validated_production_checkpoint_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket", "urllib"):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged, [])
        for forbidden in ("official_eval", "evaluate_", "api_key", "os.environ"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
