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

from deepwide_agent import v25029_evidence_conditioned_runtime as parent  # noqa: E402
from deepwide_agent import v25033_single_column_evidence_conditioned_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v24990_query_vector_paired_runtime import SyntheticRobustSearch  # noqa: E402
from test_v25025_evidence_conditioned_paired_runtime import (  # noqa: E402
    EvidenceModel,
    QUESTION as MULTI_COLUMN_QUESTION,
)


ONE_COLUMN_QUESTION = (
    "Use public sources to return one table about Alpha. "
    "Column names: Name. Preserve exact spelling."
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


class SingleColumnModel:
    def __init__(self, synthesis: str) -> None:
        self.synthesis = synthesis
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.json_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens
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
            else:
                text = json.dumps(
                    {
                        "queries": [
                            "Alpha public Name list",
                            "Alpha official Name records",
                        ]
                    }
                )
        else:
            text = self.synthesis
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SingleColumnEvidenceConditionedRuntimeTests(unittest.TestCase):
    def _run(self, module, *, question: str, inner) -> tuple[object, dict]:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: SyntheticRobustSearch(question, "Alice")
                for phase in module.PHASES
            }
            result = module.run_task(
                {"opaque_id": "task_" + "1" * 24, "question": question},
                model=model,
                searches=searches,
                limits=limits(),
            )
        return inner, module.validate_result(result)

    def test_matched_parent_fallback_becomes_primary_with_identical_effects(self) -> None:
        synthesis = "| Person |\n| --- |\n| Alice [A-1] |"
        parent_inner, parent_result = self._run(
            parent,
            question=ONE_COLUMN_QUESTION,
            inner=SingleColumnModel(synthesis),
        )
        candidate_inner, candidate = self._run(
            target,
            question=ONE_COLUMN_QUESTION,
            inner=SingleColumnModel(synthesis),
        )
        self.assertFalse(parent_result["model_success"])
        self.assertEqual(parent_result["completion_kind"], "best_effort_fallback")
        self.assertTrue(candidate["model_success"])
        self.assertEqual(candidate["completion_kind"], "primary")
        self.assertIn("| Name |", candidate["prediction"])
        self.assertIn("| Alice [A-1] |", candidate["prediction"])
        receipt = candidate["content_free_receipt"]
        self.assertTrue(receipt["single_column_normalizer_eligible"])
        self.assertTrue(receipt["single_column_normalizer_engaged"])
        self.assertEqual(receipt["normalizer_nonempty_factual_cell_rewrite_count"], 0)
        self.assertEqual(receipt["normalizer_additional_model_search_or_fetch_call_count"], 0)
        self.assertEqual(parent_inner.requests, candidate_inner.requests)
        self.assertEqual(parent_result["cost"], candidate["cost"])
        self.assertEqual(
            parent_result["content_free_receipt"]["physical_query_count"],
            receipt["physical_query_count"],
        )
        self.assertEqual(
            parent_result["content_free_receipt"]["physical_fetch_count"],
            receipt["physical_fetch_count"],
        )

    def test_ambiguous_one_column_tables_still_fail_closed(self) -> None:
        synthesis = (
            "| Person |\n| --- |\n| Alice |\n\n"
            "| Person |\n| --- |\n| Bob |"
        )
        inner, result = self._run(
            target,
            question=ONE_COLUMN_QUESTION,
            inner=SingleColumnModel(synthesis),
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.requests, 3)
        self.assertFalse(result["model_success"])
        self.assertFalse(receipt["single_column_normalizer_engaged"])
        self.assertEqual(receipt["normalizer_mode"], "ambiguous_single_column_tables")
        self.assertEqual(receipt["single_column_candidate_table_count"], 2)

    def test_multi_column_prediction_and_effects_match_frozen_parent(self) -> None:
        parent_inner, parent_result = self._run(
            parent,
            question=MULTI_COLUMN_QUESTION,
            inner=EvidenceModel(),
        )
        candidate_inner, candidate = self._run(
            target,
            question=MULTI_COLUMN_QUESTION,
            inner=EvidenceModel(),
        )
        self.assertEqual(parent_result["prediction"], candidate["prediction"])
        self.assertEqual(parent_result["cost"], candidate["cost"])
        self.assertEqual(parent_inner.requests, candidate_inner.requests)
        self.assertFalse(
            candidate["content_free_receipt"]["single_column_normalizer_eligible"]
        )
        self.assertFalse(
            candidate["content_free_receipt"]["single_column_normalizer_engaged"]
        )

    def test_zero_effect_terminal_projection_and_privileged_rejection(self) -> None:
        projection = target.project_terminal_failure(
            {"opaque_id": "task_" + "2" * 24, "question": ONE_COLUMN_QUESTION},
            failure_type="SyntheticFailure",
            elapsed_seconds=1.25,
        )
        checked = target.validate_result(projection)
        receipt = checked["content_free_receipt"]
        self.assertEqual(receipt["model_provider_request_count"], 0)
        self.assertEqual(receipt["physical_query_count"], 0)
        self.assertEqual(receipt["physical_fetch_count"], 0)

        inner = SingleColumnModel("| Person |\n| --- |\n| Alice |")
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 9):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=8,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: SyntheticRobustSearch(ONE_COLUMN_QUESTION, "Alice")
                for phase in target.PHASES
            }
            task = {
                "opaque_id": "task_" + "3" * 24,
                "question": ONE_COLUMN_QUESTION,
                "category": "forbidden",
            }
            with self.assertRaisesRegex(ValueError, "privileged"):
                target.run_task(task, model=model, searches=searches, limits=limits())
        self.assertEqual(inner.requests, 0)

    def test_resealed_receipt_tamper_fails_closed(self) -> None:
        _inner, result = self._run(
            target,
            question=ONE_COLUMN_QUESTION,
            inner=SingleColumnModel("| Person |\n| --- |\n| Alice |"),
        )
        changed = copy.deepcopy(result["content_free_receipt"])
        changed["normalizer_nonempty_factual_cell_rewrite_count"] = 1
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)

    def test_runtime_has_no_direct_network_process_or_evaluator_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25033_single_column_evidence_conditioned_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "deepwidebench",
            "eval",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        # These words may appear inside explicit false receipt fields.  No AST
        # subscript/attribute access may use them as runtime inputs.
        forbidden_fields = {
            "category",
            "question_type",
            "ground_truth",
            "answer_key",
            "evaluator_score",
            "reward",
        }
        accesses: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    accesses.add(node.slice.value)
            if isinstance(node, ast.Attribute):
                accesses.add(node.attr)
        self.assertFalse(accesses & forbidden_fields)


if __name__ == "__main__":
    unittest.main()
