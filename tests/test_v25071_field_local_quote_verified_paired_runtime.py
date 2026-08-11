from __future__ import annotations

import ast
import json
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25071_field_local_quote_verified_paired_runtime as target  # noqa: E402
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


class FieldLocalModel:
    def __init__(self, *, proposal: str = "valid", same: bool = False) -> None:
        self.proposal = proposal
        self.same = same
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
                        "columns": ["Entity", "Value"],
                        "queries": ["Alpha one", "Alpha two", "Alpha three", "Alpha four"],
                    }
                )
            elif self.proposal == "valid":
                matched = re.search(r'\{"record_id":[^}]+\}', user)
                if matched is None:
                    raise AssertionError("synthetic record anchor absent")
                anchor = matched.group(0)
                text = json.dumps(
                    {
                        "records": [
                            {
                                "page_ordinal": 1,
                                "record_anchor": anchor,
                                "row_identity": "Alpha",
                                "fields": [
                                    {
                                        "column": "Value",
                                        "quote": anchor,
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
            value = "999" if "FIELD_LOCAL_QUOTE_VERIFIED_RECORD" in user else "111"
            if self.same:
                value = "111"
            text = f"| Entity | Value |\n|---|---|\n| Alpha | {value} |"
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class FieldLocalPairedRuntimeTests(unittest.TestCase):
    def _run(self, *, proposal="valid", same=False, failing=False):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = FieldLocalModel(proposal=proposal, same=same)
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
                else SyntheticRobustSearch(QUESTION, "999")
            )
            searches = {
                target.PHASES[0]: first,
                target.PHASES[1]: SyntheticRobustSearch(QUESTION, "999"),
            }
            result = target.run_paired_task(
                {"opaque_id": "task_0123456789abcdef01234567", "question": QUESTION},
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return inner, searches, target.validate_result(result)

    def test_shared_retrieval_field_local_representation_and_budget(self) -> None:
        inner, searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 4)
        self.assertEqual(receipt["shared_model_logical_call_count"], 2)
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 10)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertTrue(result["prediction_changed"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])
        for arm in target.ARMS:
            self.assertEqual(receipt["arm_metrics"][arm]["effective_model_logical_call_count"], 3)
        self.assertEqual(searches[target.PHASES[0]].calls, 1)

    def test_invalid_and_transport_failed_proposal_preserve_both_syntheses(self) -> None:
        for proposal in ("invalid", "failure"):
            inner, _searches, result = self._run(proposal=proposal, same=True)
            with self.subTest(proposal=proposal):
                self.assertEqual(inner.requests, 4)
                self.assertFalse(result["candidate_evidence_changed"])
                self.assertFalse(result["prediction_changed"])
                self.assertTrue(all(result["model_success"].values()))

    def test_first_wave_failure_is_terminal_without_retry(self) -> None:
        inner, _searches, result = self._run(failing=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 1)
        self.assertEqual(receipt["physical_model_logical_call_count"], 1)
        self.assertFalse(receipt["proposal_model_call_attempted"])
        self.assertEqual(receipt["first_synthesis_arm"], "none")
        self.assertFalse(any(result["model_success"].values()))

    def test_runtime_ast_is_label_blind_and_has_no_direct_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25071_field_local_quote_verified_paired_runtime.py"
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
