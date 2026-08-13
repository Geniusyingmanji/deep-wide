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
from deepwide_agent import v25271_validated_production_checkpoint_runtime as checkpoint  # noqa: E402
from deepwide_agent import v25278_paired_checkpoint_reliability_runtime as target  # noqa: E402
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


class V25278PairedCheckpointReliabilityRuntimeTests(unittest.TestCase):
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
            result = target.run_paired_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, budget, target.validate_result(result)

    def test_one_real_forward_projects_fixed_postcheckpoint_candidate(self) -> None:
        inner, budget, result = self._run()
        control = result["control_result"]
        candidate = result["candidate_recovery_result"]
        receipt = result["content_free_paired_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertTrue(receipt["paired_projection_eligible"])
        self.assertEqual(receipt["eligibility_reason"], "clean_trusted_checkpoint")
        self.assertEqual(control["prediction"], candidate["prediction"])
        self.assertEqual(control["prediction_kind"], candidate["prediction_kind"])
        self.assertEqual(
            control["production_checkpoint"], candidate["production_checkpoint"]
        )
        self.assertEqual(control["cost"], candidate["cost"])
        self.assertEqual(
            candidate["recovered_failure_stages"], [target.INJECTED_STAGE]
        )
        self.assertEqual(
            candidate["recovered_failure_types"],
            {target.INJECTED_STAGE: target.INJECTED_FAILURE_TYPE},
        )
        self.assertEqual(
            result["candidate_stage_receipt"]["outer_physical_budget_receipt"],
            result["control_stage_receipt"]["outer_physical_budget_receipt"],
        )
        self.assertEqual(
            result["control_stage_receipt"]["outer_physical_budget_receipt"],
            budget.receipt(),
        )
        for field in (
            "candidate_additional_query_count",
            "candidate_additional_fetch_count",
            "candidate_additional_model_forward_count",
            "candidate_additional_system_total_tokens",
            "positive_signed_credit_count",
        ):
            self.assertEqual(receipt[field], 0)

    def test_deterministic_production_fallback_is_projected_from_same_checkpoint(self) -> None:
        inner = CompatibleModel()
        original = inner.complete

        def fail_third(system, user, *, max_output_tokens, json_mode=False):
            if inner.logical_calls == 2:
                from deepwide_agent.clients import ModelRequestError

                inner.logical_calls += 1
                inner.requests += 1
                inner.attempts += 1
                raise ModelRequestError("hidden transport detail")
            return original(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )

        inner.complete = fail_third
        observed, _budget, result = self._run(inner=inner)
        control = result["control_result"]
        candidate = result["candidate_recovery_result"]
        self.assertEqual(observed.logical_calls, 3)
        self.assertEqual(control["prediction_kind"], "fallback")
        self.assertEqual(
            control["production_checkpoint"]["checkpoint_kind"],
            "deterministic_fallback",
        )
        self.assertEqual(candidate["prediction"], control["prediction"])
        self.assertEqual(candidate["prediction_kind"], "fallback")
        self.assertEqual(
            candidate["content_free_receipt"]["recovery_disposition"],
            "deterministic_fallback_preserved_after_post_checkpoint_failure",
        )
        self.assertNotIn("hidden transport detail", str(result))

    def test_precheckpoint_control_failure_is_ineligible_and_fail_closed(self) -> None:
        with mock.patch.object(
            sparse.parent,
            "run_paired_task",
            side_effect=ValueError("hidden precheckpoint detail"),
        ):
            inner, _budget, result = self._run()
        receipt = result["content_free_paired_receipt"]
        self.assertEqual(inner.logical_calls, 0)
        self.assertEqual(
            result["control_result"]["prediction_kind"], "visible_fallback"
        )
        self.assertFalse(receipt["paired_projection_eligible"])
        self.assertEqual(
            receipt["eligibility_reason"], "control_has_no_trusted_checkpoint"
        )
        self.assertIsNone(result["candidate_recovery_result"])
        self.assertIsNone(result["candidate_stage_receipt"])
        self.assertNotIn("hidden precheckpoint detail", str(result))

    def test_naturally_recovered_control_is_not_reprojected(self) -> None:
        with mock.patch.object(
            checkpoint,
            "_build_result",
            side_effect=ValueError("hidden natural recovery detail"),
        ):
            inner, _budget, result = self._run()
        receipt = result["content_free_paired_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["control_result"]["role"], checkpoint.RECOVERY_ROLE)
        self.assertFalse(receipt["paired_projection_eligible"])
        self.assertEqual(
            receipt["eligibility_reason"],
            "control_not_clean_checkpoint_result",
        )
        self.assertIsNone(result["candidate_recovery_result"])
        self.assertNotIn("hidden natural recovery detail", str(result))

    def test_resealed_nested_result_receipt_stage_or_credit_tamper_fails(self) -> None:
        _inner, _budget, result = self._run()
        for kind in (
            "control",
            "candidate",
            "candidate_stage",
            "receipt_hidden",
            "additional_effect",
            "credit",
        ):
            changed = copy.deepcopy(result)
            if kind == "control":
                changed["control_result"]["prediction"] += "x"
            elif kind == "candidate":
                candidate = changed["candidate_recovery_result"]
                candidate["recovered_failure_types"][target.INJECTED_STAGE] = (
                    "ValueError"
                )
                candidate.pop("result_payload_sha256")
                candidate["result_payload_sha256"] = payload_sha256(candidate)
                changed["candidate_recovery_result_payload_sha256"] = candidate[
                    "result_payload_sha256"
                ]
            elif kind == "candidate_stage":
                stage = changed["candidate_stage_receipt"]
                stage["stage_failure_types"][
                    target.INJECTED_STAGE
                ] = "ValueError"
                stage.pop("receipt_payload_sha256")
                stage["receipt_payload_sha256"] = payload_sha256(stage)
            elif kind == "receipt_hidden":
                changed["content_free_paired_receipt"]["hidden"] = True
            elif kind == "additional_effect":
                changed["content_free_paired_receipt"][
                    "candidate_additional_model_forward_count"
                ] = 1
            else:
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_receipt_rejects_ineligible_candidate_or_false_equality(self) -> None:
        _inner, _budget, result = self._run()
        receipt = result["content_free_paired_receipt"]
        for kind in ("eligible", "equality", "stage", "hidden"):
            changed = copy.deepcopy(receipt)
            if kind == "eligible":
                changed["paired_projection_eligible"] = False
            elif kind == "equality":
                changed["control_and_candidate_prediction_equal"] = False
            elif kind == "stage":
                changed["candidate_injected_failure_stage"] = "result_envelope_build"
            else:
                changed["hidden"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_source_is_label_blind_and_has_no_effect_or_evaluator_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25278_paired_checkpoint_reliability_runtime.py"
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
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
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
