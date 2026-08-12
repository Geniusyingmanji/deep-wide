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

from deepwide_agent import v25139_targeted_revision_runtime as target  # noqa: E402
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


def limits(**changes: int) -> ScoreFirstLimits:
    values = {
        "wall_seconds": 240,
        "model_calls": 3,
        "search_queries": 4,
        "fetch_targets": 10,
        "search_results_per_query": 3,
        "evidence_chars": 60_000,
        "page_chars": 5_000,
    }
    values.update(changes)
    return ScoreFirstLimits(**values)


class CapturingModel(CompatibleModel):
    def __init__(self, *, revision_mode: str = "normal") -> None:
        super().__init__()
        self.revision_mode = revision_mode
        self.prompts: list[tuple[str, str]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.prompts.append((str(system), str(user)))
        if self.logical_calls == 3 and self.revision_mode != "normal":
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            rows = {
                "unsupported_and_supported": (
                    "| .in | generic | 999 |"
                ),
                "unknown": "| .in | country-code | Unknown |",
                "key": "| .us | country-code | 999 |",
                "added_row": (
                    "| .in | country-code | 999 |\n"
                    "| .extra | country-code | 999 |"
                ),
            }
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                + rows[self.revision_mode]
            )
            return ModelResult(text=text, usage={}, response_id=None, attempts=1)
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class FailingTargetedProviderModel(CapturingModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 3:
            self.prompts.append((str(system), str(user)))
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            raise ModelRequestError("synthetic targeted provider failure")
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class TargetedRevisionRuntimeTests(unittest.TestCase):
    def _run(self, *, field_page: bool, inner=None, post_effect_failure=False):
        inner = inner or CapturingModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
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
            original = target.sparse_parent.parent.validate_result
            if post_effect_failure:
                def fail_after_effect(value):
                    checked = original(value)
                    if checked["content_free_receipt"][
                        "physical_model_logical_call_count"
                    ]:
                        raise RuntimeError("synthetic post-effect projection failure")
                    return checked

                target.sparse_parent.parent.validate_result = fail_after_effect
            try:
                result = target.run_task(
                    TASK,
                    model=model,
                    searches=searches,
                    limits=limits(),
                )
            finally:
                target.sparse_parent.parent.validate_result = original
        return inner, searches, target.validate_result(result)

    def test_no_gain_keeps_three_forwards_and_exact_production(self) -> None:
        inner, _searches, result = self._run(field_page=False)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["targeted_revision_entry_count"], 0)
        self.assertFalse(receipt["targeted_prompt_built"])
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertEqual(result["cost"]["model"]["requests"], 3)

    def test_gain_uses_production_table_verified_delta_and_context_nonexpansion(self) -> None:
        inner, _searches, result = self._run(field_page=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["targeted_revision_entry_count"], 1)
        self.assertEqual(receipt["revision_underlying_provider_forward_count"], 1)
        self.assertTrue(receipt["targeted_prompt_built"])
        self.assertTrue(receipt["production_table_conditioned"])
        self.assertGreaterEqual(receipt["verified_incremental_page_count"], 1)
        self.assertGreaterEqual(receipt["supplied_incremental_page_count"], 1)
        self.assertLessEqual(
            receipt["targeted_prompt_character_count"],
            receipt["original_candidate_prompt_character_count"],
        )
        system, user = inner.prompts[-1]
        self.assertEqual(system, target.TARGETED_REVISION_SYSTEM)
        self.assertIn("COMPLETED PRODUCTION TABLE", user)
        self.assertIn(result["production_prediction"], user)
        self.assertIn("candidate-only JSONL", user)
        self.assertNotIn("Stable control material 111", user)
        self.assertIn("999", result["prediction"])
        self.assertEqual(receipt["applied_changed_cell_count"], 1)

    def test_unsupported_cell_is_preserved_while_supported_cell_is_applied(self) -> None:
        _inner, _searches, result = self._run(
            field_page=True,
            inner=CapturingModel(revision_mode="unsupported_and_supported"),
        )
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["projection_valid"])
        self.assertEqual(receipt["proposed_changed_cell_count"], 2)
        self.assertEqual(receipt["applied_changed_cell_count"], 1)
        self.assertEqual(receipt["rejected_changed_cell_count"], 1)
        self.assertIn("country-code", result["prediction"])
        self.assertNotIn("generic", result["prediction"])
        self.assertIn("999", result["prediction"])

    def test_known_to_unknown_is_filtered_to_production(self) -> None:
        _inner, _searches, result = self._run(
            field_page=True, inner=CapturingModel(revision_mode="unknown")
        )
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["projection_valid"])
        self.assertEqual(receipt["applied_changed_cell_count"], 0)
        self.assertEqual(receipt["rejected_changed_cell_count"], 1)
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertIn("111", result["prediction"])

    def test_key_or_row_shape_mutation_fails_closed_to_production(self) -> None:
        for mode in ("key", "added_row"):
            with self.subTest(mode=mode):
                _inner, _searches, result = self._run(
                    field_page=True, inner=CapturingModel(revision_mode=mode)
                )
                receipt = result["content_free_receipt"]
                parent = result["parent_result"]["content_free_receipt"]
                self.assertTrue(receipt["projection_failure_present"])
                self.assertTrue(parent["revision_failure_present"])
                self.assertTrue(receipt["production_prediction_preserved_on_failure"])
                self.assertEqual(result["prediction"], result["production_prediction"])

    def test_targeted_provider_failure_preserves_production(self) -> None:
        inner, _searches, result = self._run(
            field_page=True, inner=FailingTargetedProviderModel()
        )
        receipt = result["content_free_receipt"]
        parent = result["parent_result"]["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["provider_failure_present"])
        self.assertTrue(parent["revision_failure_present"])
        self.assertTrue(receipt["production_prediction_preserved_on_failure"])
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_parent_posteffect_failure_preserves_production(self) -> None:
        inner, _searches, result = self._run(
            field_page=True, post_effect_failure=True
        )
        receipt = result["content_free_receipt"]
        parent = result["parent_result"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertIsNone(parent["parent_result"])
        self.assertTrue(parent["content_free_receipt"]["post_effect_failure_present"])
        self.assertTrue(receipt["parent_post_effect_failure_present"])
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertTrue(receipt["production_prediction_preserved_on_failure"])

    def test_conflicting_pages_reject_change(self) -> None:
        production = (
            "```markdown\n| Package | Version |\n| --- | --- |\n"
            "| Alpha | 1.0 |\n```"
        )
        candidate = production.replace("1.0", "2.0")
        pages = [
            {
                "url": "https://example.test/alpha",
                "title": "Alpha Version",
                "content": "Alpha Version 2.0",
            },
            {
                "url": "https://example.test/alpha/history",
                "title": "Alpha Version",
                "content": "Alpha Version 1.0",
            },
        ]
        projected, counts = target.project_supported_revision(
            production,
            candidate,
            columns=("Package", "Version"),
            pages=pages,
        )
        self.assertEqual(projected, production)
        self.assertEqual(counts["conflicting_changed_cell_count"], 1)
        self.assertEqual(counts["applied_changed_cell_count"], 0)

    def test_distant_or_substring_value_cooccurrence_is_not_support(self) -> None:
        production = (
            "```markdown\n| Package | Version |\n| --- | --- |\n"
            "| Alpha | 1.0 |\n```"
        )
        candidate = production.replace("1.0", "2.0")
        for content in (
            "Alpha Version " + "filler " * 300 + "2.0",
            "Alpha Version 12.0",
        ):
            projected, counts = target.project_supported_revision(
                production,
                candidate,
                columns=("Package", "Version"),
                pages=[
                    {
                        "url": "https://example.test/alpha",
                        "title": "Alpha Version",
                        "content": content,
                    }
                ],
            )
            with self.subTest(content=content[-20:]):
                self.assertEqual(projected, production)
                self.assertEqual(counts["applied_changed_cell_count"], 0)
                self.assertEqual(counts["rejected_changed_cell_count"], 1)

    def test_privileged_or_budget_drift_fails_before_any_effect(self) -> None:
        for mode in ("privileged", "budget"):
            inner = CapturingModel()
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
                output_root = Path(raw)
                slots = output_root / "slots"
                slots.mkdir()
                for index in range(1, 5):
                    (slots / f"slot_{index:02d}.lock").write_text("{}\n")
                model = DeadlineAwareGlobalModelSlotLimiter(
                    inner,
                    slot_directory=slots,
                    output_root=output_root,
                    slot_cap=4,
                    absolute_deadline=time.monotonic() + 240,
                )
                searches = {
                    phase: GroundedFrontierSearch(QUESTION, phase)
                    for phase in target.PHASES
                }
                task = (
                    {**TASK, "question_type": "forbidden"}
                    if mode == "privileged"
                    else TASK
                )
                chosen = limits(model_calls=2) if mode == "budget" else limits()
                with self.assertRaises(ValueError):
                    target.run_task(
                        task, model=model, searches=searches, limits=chosen
                    )
            self.assertEqual(inner.logical_calls, 0)
            self.assertTrue(all(search.calls == 0 for search in searches.values()))

    def test_receipt_tamper_and_parent_reseal_fail_closed(self) -> None:
        _inner, _searches, result = self._run(field_page=True)
        for mode in ("applied", "context", "launch", "parent"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if mode == "applied":
                receipt["applied_changed_cell_count"] = 0
            elif mode == "context":
                receipt["context_cap_preserved"] = False
            elif mode == "launch":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["parent_result_payload_sha256"] = "0" * 64
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_receipt_is_content_free(self) -> None:
        _inner, _searches, result = self._run(field_page=True)
        semantic = {
            key: value
            for key, value in result["content_free_receipt"].items()
            if not key.endswith("sha256")
        }
        encoded = json.dumps(semantic, ensure_ascii=False)
        for forbidden in (
            "New Delhi",
            "India",
            "IANA",
            "https://",
            "111",
            "999",
            TASK["opaque_id"],
        ):
            self.assertNotIn(forbidden, encoded)

    def test_module_is_label_blind_build_only_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25139_targeted_revision_runtime.py"
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
