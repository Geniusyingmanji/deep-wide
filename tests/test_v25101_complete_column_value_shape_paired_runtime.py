from __future__ import annotations

import ast
import copy
import json
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

from deepwide_agent import v25101_complete_column_value_shape_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v24990_query_vector_paired_runtime import (  # noqa: E402
    FailingSyntheticRobustSearch,
    SyntheticRobustSearch,
)


QUESTION = (
    "Use public sources and the visible PyPI authority to return one table about "
    "<ENTITY>Alpha</ENTITY>. Column names: Entity, Value. Preserve exact spelling."
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


class AttributionModel:
    def __init__(self, *, proposal: str = "valid", alternate_unexposed: bool = False) -> None:
        self.proposal = proposal
        self.alternate_unexposed = alternate_unexposed
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.json_calls = 0
        self.synthesis_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
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
                        "columns": ["Entity", "Value"],
                        "queries": ["Alpha one", "Alpha two", "Alpha three", "Alpha four"],
                    }
                )
            elif self.proposal == "valid":
                text = json.dumps(
                    {
                        "records": [
                            {
                                "page_ordinal": 1,
                                "columns": [
                                    {
                                        "column": "Value",
                                        "status": "found",
                                        "source_field": "Value",
                                        "value": "999",
                                    }
                                ],
                            }
                        ]
                    }
                )
            elif self.proposal == "invalid":
                text = "not-json"
            else:
                raise RuntimeError("proposal failure")
        else:
            self.synthesis_calls += 1
            if "VALUE_SHAPE_PARTIAL_RECORD" in user:
                value = "999"
            elif self.alternate_unexposed:
                value = "111" if self.synthesis_calls == 1 else "222"
            else:
                value = "111"
            text = f"| Entity | Value |\n|---|---|\n| Alpha | {value} |"
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class AuthorityIdentitySearch(SyntheticRobustSearch):
    def __init__(self, question: str, value: str, *, mode: str) -> None:
        super().__init__(question, value)
        self._mode = mode

    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if output and output[0]["results"]:
            if self._mode in {"single", "multiple"}:
                first = output[0]["results"][0]
                first["url"] = "https://pypi.org/project/Alpha"
                first["fetch_url"] = first["url"]
            if self._mode == "multiple":
                second = output[0]["results"][1]
                second["url"] = "https://docs.example.test/Alpha"
                second["fetch_url"] = second["url"]
        return output

    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        for batch in output:
            for result in batch["results"]:
                if result["url"].endswith("/Alpha"):
                    authority = "PyPI" if "pypi.org" in result["url"] else "Docs"
                    result["title"] = f"Alpha | {authority}"
        return output


class CompleteColumnValueShapePairedRuntimeTests(unittest.TestCase):
    def _run(
        self,
        *,
        proposal: str = "valid",
        alternate_unexposed: bool = False,
        first_mode: str = "multiple",
        failing: bool = False,
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = AttributionModel(
                proposal=proposal,
                alternate_unexposed=alternate_unexposed,
            )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            first = (
                FailingSyntheticRobustSearch(QUESTION, "999")
                if failing
                else AuthorityIdentitySearch(QUESTION, "999", mode=first_mode)
            )
            searches = {
                target.PHASES[0]: first,
                target.PHASES[1]: AuthorityIdentitySearch(QUESTION, "999", mode="none"),
            }
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return inner, searches, target.validate_result(result)

    def test_visible_authority_resolves_multiple_pages_and_change_is_attributable(self) -> None:
        inner, searches, result = self._run(first_mode="multiple")
        receipt = result["content_free_receipt"]
        binding = receipt["record_binding_receipt"]
        parent = binding["parent_value_shape_receipt"]
        selection = parent["authority_selection_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 10)
        self.assertTrue(selection["authority_tiebreak_selected"])
        self.assertGreaterEqual(selection["strict_identity_page_count"], 2)
        self.assertTrue(binding["complete_column_proposal_strictly_valid"])
        self.assertEqual(binding["submitted_column_disposition_count"], 1)
        self.assertEqual(binding["found_column_disposition_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertTrue(receipt["prediction_changed"])
        self.assertTrue(receipt["attributable_prediction_change"])
        self.assertFalse(receipt["prediction_identity_handoff_applied"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])
        self.assertEqual(searches[target.PHASES[0]].calls, 1)

    def test_unexposed_independent_sampling_difference_is_identity_handoff(self) -> None:
        inner, _searches, result = self._run(
            proposal="invalid",
            alternate_unexposed=True,
            first_mode="single",
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertEqual(inner.synthesis_calls, 2)
        self.assertFalse(receipt["candidate_evidence_changed"])
        self.assertTrue(receipt["prediction_identity_handoff_applied"])
        self.assertFalse(receipt["prediction_changed"])
        self.assertFalse(receipt["attributable_prediction_change"])
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_transport_failed_proposal_preserves_budget_and_handoff(self) -> None:
        inner, _searches, result = self._run(
            proposal="failure",
            alternate_unexposed=True,
            first_mode="single",
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertFalse(receipt["candidate_evidence_changed"])
        self.assertTrue(receipt["prediction_identity_handoff_applied"])
        self.assertFalse(result["prediction_changed"])
        self.assertTrue(all(result["model_success"].values()))

    def test_representation_validation_failure_is_safe_identity_handoff(self) -> None:
        with mock.patch.object(
            target.binding,
            "build_representation",
            side_effect=ValueError("synthetic representation failure"),
        ):
            inner, _searches, result = self._run(
                proposal="valid",
                alternate_unexposed=True,
                first_mode="single",
            )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertTrue(receipt["representation_validation_failed"])
        self.assertEqual(receipt["representation_failure_type"], "ValueError")
        self.assertIsNone(receipt["record_binding_receipt"])
        self.assertFalse(receipt["candidate_evidence_changed"])
        self.assertTrue(receipt["prediction_identity_handoff_applied"])
        self.assertFalse(receipt["prediction_changed"])
        self.assertTrue(all(result["model_success"].values()))
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_first_wave_failure_is_terminal_without_retry(self) -> None:
        inner, _searches, result = self._run(failing=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 1)
        self.assertEqual(receipt["physical_model_logical_call_count"], 1)
        self.assertFalse(receipt["proposal_model_call_attempted"])
        self.assertEqual(receipt["first_synthesis_arm"], "none")
        self.assertFalse(receipt["prediction_identity_handoff_applied"])
        self.assertFalse(any(result["model_success"].values()))

    def test_post_synthesis_accounting_failure_is_terminal_no_go_result(self) -> None:
        with mock.patch.object(
            target.counters,
            "_delta",
            side_effect=ValueError("synthetic accounting failure"),
        ):
            inner, _searches, result = self._run(first_mode="multiple")
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertEqual(result["status"], "terminal_accounting_failure")
        self.assertTrue(result["post_synthesis_accounting_or_receipt_validation_failed"])
        self.assertEqual(receipt["failure_stage"], "post_synthesis_accounting")
        self.assertEqual(receipt["failure_type"], "ValueError")
        self.assertTrue(receipt["failure_is_terminal_and_requires_mechanism_no_go"])
        self.assertIsNone(result["cost"])
        self.assertIsNone(result["failure_types"])
        self.assertFalse(any(result["model_success"].values()))
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_receipt_construction_failure_is_terminal_no_go_result(self) -> None:
        with mock.patch.object(
            target,
            "_receipt",
            side_effect=ValueError("synthetic receipt failure"),
        ):
            inner, _searches, result = self._run(first_mode="multiple")
        self.assertEqual(inner.requests, 4)
        self.assertEqual(result["status"], "terminal_accounting_failure")
        self.assertEqual(
            result["content_free_receipt"]["failure_stage"],
            "receipt_construction",
        )
        self.assertEqual(result["content_free_receipt"]["failure_type"], "ValueError")

    def test_result_validation_failure_is_terminal_no_go_result(self) -> None:
        original = target.validate_result

        def fail_standard(value):
            if value.get("status") == "terminal":
                raise ValueError("synthetic result validation failure")
            return original(value)

        with mock.patch.object(target, "validate_result", side_effect=fail_standard):
            inner, _searches, result = self._run(first_mode="multiple")
        self.assertEqual(inner.requests, 4)
        self.assertEqual(result["status"], "terminal_accounting_failure")
        self.assertEqual(
            result["content_free_receipt"]["failure_stage"],
            "result_validation",
        )

    def test_resealed_accounting_failure_credit_or_launch_tamper_fails(self) -> None:
        receipt = target._accounting_failure_receipt(
            failure_stage="post_synthesis_accounting",
            failure_type="ValueError",
        )
        for name in (
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
        ):
            changed = copy.deepcopy(receipt)
            changed[name] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(name=name), self.assertRaises(ValueError):
                target.validate_accounting_failure_receipt(changed)

    def test_runtime_ast_is_label_blind_and_has_no_direct_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25101_complete_column_value_shape_paired_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
