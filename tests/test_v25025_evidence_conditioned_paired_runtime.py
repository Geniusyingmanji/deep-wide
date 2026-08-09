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

from deepwide_agent import v25025_evidence_conditioned_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    FailingSyntheticRobustSearch,
    SyntheticRobustSearch,
)


QUESTION = (
    "Use public sources to return one table about Alpha. "
    "Column names: Entity, Value. Preserve exact spelling."
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


class EvidenceModel:
    def __init__(self, *, valid_refinement: bool = True) -> None:
        self.valid_refinement = valid_refinement
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.json_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if json_mode:
            self.json_calls += 1
            if self.json_calls == 1:
                text = json.dumps(
                    {
                        "language": "English",
                        "columns": ["wrong"],
                        "queries": ["Alpha clue"],
                    }
                )
            elif self.valid_refinement:
                text = json.dumps(
                    {
                        "queries": [
                            "Alpha 111 official list",
                            "Alpha 111 Entity Value records",
                        ]
                    }
                )
            else:
                text = "not-json"
        else:
            value = "999" if "999" in user else "111"
            text = f"| Entity | Value |\n|---|---|\n| Alpha | {value} |"
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class EvidenceConditionedPairedRuntimeTests(unittest.TestCase):
    def _run(self, *, valid_refinement=True, values=("111", "111", "999")):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = EvidenceModel(valid_refinement=valid_refinement)
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                target.PHASES[0]: SyntheticRobustSearch(QUESTION, values[0]),
                target.CONTROL_ARM: SyntheticRobustSearch(QUESTION, values[1]),
                target.CANDIDATE_ARM: SyntheticRobustSearch(QUESTION, values[2]),
            }
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=[target.CONTROL_ARM, target.CANDIDATE_ARM],
            )
        return inner, searches, target.validate_result(result)

    def test_shared_plan_refinement_and_per_arm_caps(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["refinement_strategy_applied"])
        self.assertTrue(receipt["query_vectors_differ_only_in_second_wave"])
        self.assertEqual(receipt["shared_model_call_count"], 2)
        self.assertEqual(receipt["model_logical_call_count"], 4)
        self.assertEqual(inner.requests, 4)
        self.assertEqual(receipt["physical_query_count"], 6)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)
        for arm in target.ARMS:
            metric = receipt["arm_metrics"][arm]
            self.assertEqual(metric["executed_queries"], 4)
            self.assertLessEqual(metric["fetch_attempts"], 10)
            self.assertTrue(metric["model_success"])
            self.assertLessEqual(
                receipt["shared_model_call_count"] + int(metric["synthesis_attempted"]),
                3,
            )
        self.assertTrue(result["prediction_changed"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])
        self.assertEqual(searches[target.PHASES[0]].calls, 1)

    def test_invalid_refinement_is_exact_query_handoff(self) -> None:
        inner, _searches, result = self._run(
            valid_refinement=False, values=("111", "111", "111")
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertFalse(receipt["refinement_strategy_applied"])
        self.assertTrue(receipt["exact_legacy_second_wave_handoff"])
        self.assertFalse(receipt["query_vectors_differ_only_in_second_wave"])
        self.assertFalse(result["prediction_changed"])

    def test_shared_wave_failure_skips_refinement_and_synthesis(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = EvidenceModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                target.PHASES[0]: FailingSyntheticRobustSearch(QUESTION, "111"),
                target.CONTROL_ARM: SyntheticRobustSearch(QUESTION, "111"),
                target.CANDIDATE_ARM: SyntheticRobustSearch(QUESTION, "999"),
            }
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
            )
        checked = target.validate_result(result)
        receipt = checked["content_free_receipt"]
        self.assertEqual(inner.requests, 1)
        self.assertFalse(receipt["refinement_model_call_attempted"])
        self.assertEqual(receipt["model_logical_call_count"], 1)
        self.assertEqual(receipt["actual_first_synthesis_arm"], "none")

    def test_tamper_and_shared_search_client_fail_closed(self) -> None:
        _inner, _searches, result = self._run()
        changed = copy.deepcopy(result)
        changed["content_free_receipt"]["physical_model_call_cap"] = 5
        with self.assertRaises(ValueError):
            target.validate_result(changed)

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            model = DeadlineAwareGlobalModelSlotLimiter(
                EvidenceModel(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            shared = SyntheticRobustSearch(QUESTION, "111")
            with self.assertRaisesRegex(ValueError, "three distinct"):
                target.run_paired_task(
                    {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                    model=model,
                    searches={phase: shared for phase in target.PHASES},
                    limits=limits(),
                )

    def test_receipts_are_content_free_and_entropy_free(self) -> None:
        _inner, _searches, result = self._run()
        # Cryptographic seals are opaque digests and can coincidentally contain
        # a short fixture substring.  Scan the semantic receipt payload, while
        # separately relying on validate_result() to verify every seal.
        def without_seals(value):
            if isinstance(value, dict):
                return {
                    key: without_seals(item)
                    for key, item in value.items()
                    if not key.endswith("_sha256")
                }
            if isinstance(value, list):
                return [without_seals(item) for item in value]
            return value

        serialized = json.dumps(
            without_seals(result["content_free_receipt"]), sort_keys=True
        )
        for forbidden in ("Alpha", "111", "999", "official-"):
            self.assertNotIn(forbidden, serialized)
        self.assertFalse(
            result["content_free_receipt"]["entropy_or_information_gain_assigns_signed_credit"]
        )
        self.assertFalse(result["benchmark_launch_or_evaluator_authorized"])

    def test_module_has_no_direct_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25025_evidence_conditioned_paired_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("os", "pathlib", "subprocess", "requests", "deepwidebench"):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden in ("ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
