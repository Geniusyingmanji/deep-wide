from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25127_causally_coupled_target_record_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    CompatibleModel,
    GroundedFrontierSearch,
    QUESTION,
    TASK,
)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class CausallyCoupledTargetRecordRuntimeTests(unittest.TestCase):
    def _run(self, *, field_page: bool = True):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            inner = CompatibleModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(
                    QUESTION, phase, field_page=field_page
                )
                for phase in target.PHASES
            }
            result = target.run_paired_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return inner, searches, target.validate_result(result)

    def test_positive_gain_allows_only_attributable_prediction_change(self) -> None:
        inner, _searches, result = self._run(field_page=True)
        receipt = result["content_free_receipt"]
        coupling = result["causal_coupling_receipt"]
        salience = coupling["prompt_salience_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["retrieval_mechanism_engaged"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertTrue(receipt["attributable_prediction_change"])
        self.assertFalse(coupling["prediction_identity_handoff_applied"])
        self.assertEqual(salience["grounded_prompt_checklist_count"], 1)
        self.assertEqual(salience["synthesis_prompt_count"], 2)
        self.assertTrue(
            all(
                salience["arm_observations"][arm][
                    "second_wave_records_prioritized"
                ]
                for arm in target.ARMS
            )
        )
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)

    def test_no_positive_gain_forces_identity_after_equal_cost_synthesis(self) -> None:
        inner, _searches, result = self._run(field_page=False)
        receipt = result["content_free_receipt"]
        coupling = result["causal_coupling_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertFalse(receipt["retrieval_mechanism_engaged"])
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(receipt["attributable_prediction_change"])
        self.assertTrue(coupling["prediction_identity_handoff_applied"])
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_prompt_reorder_is_length_preserving_and_content_neutral(self) -> None:
        evidence = """[E0001] kind=fetched_page
first

[E0002] kind=fetched_page
second

[E0003] kind=fetched_page
third"""
        user = (
            "VISIBLE QUESTION:\nq\n\nBOUNDED WEB MATERIAL:\n"
            + evidence
            + " " * 17
            + "\n\nProduce the best-supported answer possible now"
        )
        value, records, second, changed = target._prioritize_second_wave(user, 1)
        self.assertEqual(len(value), len(user))
        self.assertEqual(records, 3)
        self.assertEqual(second, 2)
        self.assertTrue(changed)
        self.assertLess(value.index("second"), value.index("first"))
        self.assertCountEqual(value, user)
        self.assertTrue(value[: value.index("\n\nProduce")].endswith(" " * 17))

    def test_resealed_coupling_salience_or_parent_tamper_fails(self) -> None:
        _inner, _searches, result = self._run(field_page=True)
        for kind in ("coupling", "salience", "parent"):
            changed = copy.deepcopy(result)
            coupling = changed["causal_coupling_receipt"]
            if kind == "coupling":
                coupling["prediction_identity_handoff_applied"] = True
            elif kind == "salience":
                coupling["prompt_salience_receipt"]["synthesis_prompt_count"] = 1
                coupling["prompt_salience_receipt"].pop("receipt_payload_sha256")
                coupling["prompt_salience_receipt"]["receipt_payload_sha256"] = (
                    payload_sha256(coupling["prompt_salience_receipt"])
                )
            else:
                coupling["projected_parent_result_payload_sha256"] = "0" * 64
            coupling.pop("receipt_payload_sha256")
            coupling["receipt_payload_sha256"] = payload_sha256(coupling)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_has_no_effect_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25127_causally_coupled_target_record_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
