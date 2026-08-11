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

from deepwide_agent import (  # noqa: E402
    v25134_schema_total_causal_salience_runtime as target,
)
from deepwide_agent.clients import ModelRequestError, ModelResult  # noqa: E402
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


NO_EXACT_SCHEMA = (
    "Research the public record for Alpha and return the requested table. "
    "Use the fields Entity, Value, and Date, and preserve exact spelling."
)
NO_SCHEMA = "Research the public record for Alpha and return a useful table."


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


class TotalityModel:
    def __init__(self, *, fail_plan: bool = False, invalid_plan: bool = False) -> None:
        self.fail_plan = fail_plan
        self.invalid_plan = invalid_plan
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            if self.fail_plan:
                raise ModelRequestError("synthetic plan failure")
            text = (
                "not-json"
                if self.invalid_plan
                else json.dumps(
                    {
                        "columns": ["Entity", "Value", "Date"],
                        "queries": [
                            "Alpha public record",
                            "Alpha official source",
                            "Alpha value date",
                            "Alpha public database",
                        ],
                    }
                )
            )
        elif self.logical_calls == 2:
            text = "not-json"
        else:
            columns = ["Result"] if self.fail_plan or self.invalid_plan else ["Entity", "Value", "Date"]
            separator = ["---"] * len(columns)
            values = ["Alpha"] if columns == ["Result"] else ["Alpha", "111", "2026-01-01"]
            text = (
                "| " + " | ".join(columns) + " |\n"
                "|" + "|".join(separator) + "|\n"
                "| " + " | ".join(values) + " |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class SchemaTotalCausalSalienceRuntimeTests(unittest.TestCase):
    def _run(self, question: str, inner) -> dict:
        task = {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": question,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(question, phase, field_page=False)
                for phase in target.PHASES
            }
            result = target.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=target.ARMS,
            )
        return target.validate_result(result)

    def test_explicit_schema_keeps_exact_visible_precedence(self) -> None:
        result = self._run(QUESTION, CompatibleModel())
        receipt = result["schema_totality_receipt"]
        self.assertEqual(receipt["schema_source"], "exact_visible")
        self.assertEqual(receipt["effective_column_count"], 3)
        self.assertTrue(receipt["exact_visible_schema_used"])
        self.assertFalse(receipt["provider_plan_schema_used"])
        self.assertFalse(receipt["generic_result_schema_used"])
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_absent_exact_schema_uses_same_effect_provider_columns(self) -> None:
        inner = TotalityModel()
        result = self._run(NO_EXACT_SCHEMA, inner)
        receipt = result["schema_totality_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["schema_source"], "provider_plan")
        self.assertEqual(receipt["effective_column_count"], 3)
        self.assertTrue(receipt["provider_plan_schema_used"])
        self.assertTrue(all(result["model_success"].values()))
        self.assertIn("| Entity | Value | Date |", result["predictions"][target.CONTROL_ARM])

    def test_explicit_schema_survives_plan_transport_failure(self) -> None:
        inner = CompatibleModel(fail_plan=True)
        result = self._run(QUESTION, inner)
        receipt = result["schema_totality_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["schema_source"], "exact_visible")
        self.assertTrue(receipt["exact_visible_schema_used"])
        self.assertTrue(receipt["plan_model_effect_failed"])
        self.assertTrue(all(result["model_success"].values()))

    def test_failed_or_invalid_plan_uses_generic_result_and_stays_terminal(self) -> None:
        for mode in ("failure", "invalid"):
            inner = TotalityModel(
                fail_plan=mode == "failure", invalid_plan=mode == "invalid"
            )
            result = self._run(NO_SCHEMA, inner)
            receipt = result["schema_totality_receipt"]
            self.assertEqual(receipt["schema_source"], "generic_result")
            self.assertEqual(receipt["effective_column_count"], 1)
            self.assertTrue(receipt["generic_result_schema_used"])
            self.assertEqual(inner.logical_calls, 4)
            self.assertTrue(all(result["model_success"].values()))
            self.assertIn("| Result |", result["predictions"][target.CONTROL_ARM])
            with self.subTest(mode=mode):
                if mode == "failure":
                    self.assertTrue(receipt["plan_model_effect_failed"])
                else:
                    self.assertTrue(receipt["plan_output_validation_failed"])

    def test_total_column_hierarchy_is_deterministic_and_safe(self) -> None:
        exact, exact_source = target._total_columns(
            {"columns": ["wrong"]}, QUESTION
        )
        provider, provider_source = target._total_columns(
            {"columns": ["Entity", "Value", "Date"]}, NO_EXACT_SCHEMA
        )
        generic, generic_source = target._total_columns(
            {"columns": ["Duplicate", "Duplicate"]}, NO_SCHEMA
        )
        self.assertEqual(exact_source, "exact_visible")
        self.assertEqual(exact, ("Domain", "Type", "TLD Manager"))
        self.assertEqual(provider_source, "provider_plan")
        self.assertEqual(provider, ("Entity", "Value", "Date"))
        self.assertEqual(generic_source, "generic_result")
        self.assertEqual(generic, ("Result",))

    def test_resealed_schema_source_parent_or_launch_tamper_fails(self) -> None:
        result = self._run(NO_EXACT_SCHEMA, TotalityModel())
        for kind in ("source", "parent", "launch"):
            changed = copy.deepcopy(result)
            receipt = changed["schema_totality_receipt"]
            if kind == "source":
                receipt["schema_source"] = "generic_result"
            elif kind == "parent":
                receipt["parent_result_payload_sha256"] = "0" * 64
            else:
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_runtime_field_fails_before_model_or_search_effect(self) -> None:
        inner = TotalityModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GroundedFrontierSearch(NO_SCHEMA, phase, field_page=False)
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_paired_task(
                    {
                        "opaque_id": "task_0123456789abcdef01234567",
                        "question": NO_SCHEMA,
                        "question_type": "forbidden",
                    },
                    model=model,
                    searches=searches,
                    limits=limits(),
                )
        self.assertEqual(inner.logical_calls, 0)
        self.assertTrue(all(search.calls == 0 for search in searches.values()))

    def test_module_is_label_blind_build_only_and_has_no_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25134_schema_total_causal_salience_runtime.py"
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
            "httpx",
            "socket",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        encoded = path.read_text(encoding="utf-8")
        self.assertNotIn("run_official_eval_local", encoded)
        self.assertNotIn("target/main", encoded)


if __name__ == "__main__":
    unittest.main()
