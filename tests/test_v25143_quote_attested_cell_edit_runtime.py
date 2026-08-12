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

from deepwide_agent import v25143_quote_attested_cell_edit_runtime as target  # noqa: E402
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


QUOTE = "Domain | Type | TLD Manager\n.in | country-code | 999"


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


def edit(**changes):
    value = {
        "page_ordinal": 1,
        "exact_quote": QUOTE,
        "row_identity": ".in",
        "field": "TLD Manager",
        "old_value": "111",
        "new_value": "999",
    }
    value.update(changes)
    return value


class EditModel(CompatibleModel):
    def __init__(
        self,
        *,
        edits=None,
        malformed=None,
        fail_revision=False,
    ) -> None:
        super().__init__()
        self.edits = [edit()] if edits is None else edits
        self.malformed = malformed
        self.fail_revision = fail_revision
        self.prompts: list[tuple[str, str, bool]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.prompts.append((str(system), str(user), bool(json_mode)))
        if self.logical_calls == 3:
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            if self.fail_revision:
                raise ModelRequestError("synthetic edit provider failure")
            encoded = json.dumps({"edits": self.edits})
            text = (
                "not-json"
                if self.malformed == "invalid"
                else f"```json\n{encoded}\n```"
                if self.malformed == "fenced"
                else encoded + " trailing"
                if self.malformed == "trailing"
                else '{"edits":[],"edits":[]}'
                if self.malformed == "duplicate_key"
                else encoded
            )
            return ModelResult(text=text, usage={}, response_id=None, attempts=1)
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class QuoteAttestedCellEditTests(unittest.TestCase):
    def _run(self, *, field_page=True, inner=None, post_effect_failure=False):
        inner = inner or EditModel()
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
                        raise RuntimeError("synthetic post-effect failure")
                    return checked

                target.sparse_parent.parent.validate_result = fail_after_effect
            try:
                result = target.run_task(
                    TASK, model=model, searches=searches, limits=limits()
                )
            finally:
                target.sparse_parent.parent.validate_result = original
        return inner, searches, target.validate_result(result)

    def test_no_gain_keeps_three_forwards_and_production(self) -> None:
        inner, _searches, result = self._run(field_page=False)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["cell_edit_revision_entry_count"], 0)
        self.assertEqual(receipt["underlying_provider_forward_count"], 0)
        self.assertEqual(result["prediction"], result["production_prediction"])
        self.assertEqual(result["cost"]["model"]["requests"], 3)

    def test_valid_quote_attested_edit_is_applied(self) -> None:
        inner, _searches, result = self._run()
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(inner.prompts[-1][0], target.CELL_EDIT_SYSTEM)
        self.assertTrue(inner.prompts[-1][2])
        self.assertIn(result["production_prediction"], inner.prompts[-1][1])
        self.assertTrue(receipt["cell_edit_prompt_built"])
        self.assertTrue(receipt["production_table_conditioned"])
        self.assertTrue(receipt["edit_response_strict_json"])
        self.assertTrue(receipt["edit_projection_valid"])
        self.assertEqual(receipt["model_edit_count"], 1)
        self.assertEqual(receipt["quote_attested_edit_count"], 1)
        self.assertEqual(receipt["applied_edit_count"], 1)
        self.assertEqual(receipt["rejected_edit_count"], 0)
        self.assertIn("999", result["prediction"])
        self.assertNotEqual(result["prediction"], result["production_prediction"])
        self.assertLessEqual(
            receipt["cell_edit_prompt_character_count"],
            receipt["original_candidate_prompt_character_count"],
        )

    def test_prompt_renumbers_only_pages_that_fit_context(self) -> None:
        provider = object.__new__(target.QuoteAttestedCellEditProvider)
        provider.production_prediction = (
            "```markdown\n| Domain | Type | TLD Manager |\n"
            "| --- | --- | --- |\n| .in | country-code | 111 |\n```"
        )
        provider._question = QUESTION
        pages = [
            {"title": "oversized", "content": "x" * 5_000},
            {"title": "fits", "content": QUOTE},
        ]
        inherited_system = "s"
        inherited_user = "u" * 3_000
        user, supplied = provider._edit_prompt(
            inherited_system=inherited_system,
            inherited_user=inherited_user,
            columns=("Domain", "Type", "TLD Manager"),
            pages=pages,
        )
        self.assertEqual(supplied, [pages[1]])
        self.assertIn('"page_ordinal":1', user)
        self.assertNotIn('"page_ordinal":2', user)
        self.assertLessEqual(
            len(target.CELL_EDIT_SYSTEM) + len(user),
            len(inherited_system) + len(inherited_user),
        )

    def test_wrong_quote_page_old_unknown_and_key_are_rejected(self) -> None:
        cases = {
            "quote": edit(exact_quote=QUOTE + " absent"),
            "page": edit(page_ordinal=2),
            "old": edit(old_value="222"),
            "old_surface_only": edit(old_value=" 111 "),
            "row_surface_only": edit(row_identity=".IN"),
            "field_surface_only": edit(field="tld manager"),
            "unknown": edit(new_value="Unknown"),
            "pipe": edit(new_value="999|injected"),
            "newline": edit(new_value="999\ninjected"),
            "control": edit(new_value="999\u0000injected"),
            "fence": edit(new_value="999```injected"),
            "key": edit(field="Domain", old_value=".in", new_value=".us"),
        }
        expected = {
            "quote": "quote_not_exact_unique_or_bounded",
            "page": "invalid_page_ordinal",
            "old": "old_value_mismatch",
            "old_surface_only": "old_value_mismatch",
            "row_surface_only": "row_identity_not_unique",
            "field_surface_only": "field_not_unique_or_key",
            "unknown": "new_value_unknown_empty_or_unchanged",
            "pipe": "new_value_unknown_empty_or_unchanged",
            "newline": "new_value_unknown_empty_or_unchanged",
            "control": "new_value_unknown_empty_or_unchanged",
            "fence": "new_value_unknown_empty_or_unchanged",
            "key": "field_not_unique_or_key",
        }
        for mode, proposal in cases.items():
            with self.subTest(mode=mode):
                _inner, _searches, result = self._run(
                    inner=EditModel(edits=[proposal])
                )
                receipt = result["content_free_receipt"]
                self.assertTrue(receipt["edit_projection_valid"])
                self.assertEqual(receipt["applied_edit_count"], 0)
                self.assertEqual(receipt["rejected_edit_count"], 1)
                self.assertEqual(receipt["rejection_counts"][expected[mode]], 1)
                self.assertEqual(result["prediction"], result["production_prediction"])

    def test_duplicate_and_conflicting_edits_are_rejected_atomically(self) -> None:
        _inner, _searches, result = self._run(
            inner=EditModel(edits=[edit(), edit()])
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["model_edit_count"], 2)
        self.assertEqual(receipt["quote_attested_edit_count"], 2)
        self.assertEqual(receipt["applied_edit_count"], 0)
        self.assertEqual(receipt["rejected_edit_count"], 2)
        self.assertEqual(
            receipt["rejection_counts"]["duplicate_or_conflicting_cell"], 2
        )
        self.assertEqual(result["prediction"], result["production_prediction"])

        other_quote = QUOTE.replace("999", "998")
        output, diagnostics = target.apply_quote_attested_edits(
            result["production_prediction"],
            {"edits": [edit(), edit(new_value="998", exact_quote=other_quote)]},
            columns=("Domain", "Type", "TLD Manager"),
            pages=[{"title": "", "content": QUOTE + "\n" + other_quote}],
        )
        self.assertEqual(output, result["production_prediction"])
        self.assertEqual(diagnostics["quote_attested_edit_count"], 2)
        self.assertEqual(diagnostics["applied_edit_count"], 0)
        self.assertEqual(diagnostics["rejected_edit_count"], 2)
        self.assertEqual(
            diagnostics["rejection_counts"]["duplicate_or_conflicting_cell"], 2
        )

    def test_pure_verifier_rejects_overlong_substring_or_title_only_binding(self) -> None:
        production = (
            "```markdown\n| Package | Version |\n| --- | --- |\n"
            "| Alpha | 1.0 |\n```"
        )
        cases = (
            (
                "overlong",
                "Alpha Version " + "filler " * 300 + "2.0",
                "invalid_edit_schema",
                False,
            ),
            (
                "substring",
                "Alpha Version 12.0",
                "quote_row_field_value_binding_failure",
                False,
            ),
            (
                "title_only",
                "Alpha Version 2.0",
                "quote_not_exact_unique_or_bounded",
                True,
            ),
        )
        for mode, quote, rejection, title_only in cases:
            output, diagnostics = target.apply_quote_attested_edits(
                production,
                {"edits": [edit(
                    exact_quote=quote,
                    row_identity="Alpha",
                    field="Version",
                    old_value="1.0",
                    new_value="2.0",
                )]},
                columns=("Package", "Version"),
                pages=[{
                    "title": quote if title_only else "",
                    "content": "unrelated body" if title_only else quote,
                }],
            )
            with self.subTest(mode=mode):
                self.assertEqual(output, production)
                self.assertEqual(diagnostics["applied_edit_count"], 0)
                self.assertEqual(
                    diagnostics["rejection_counts"][rejection],
                    1,
                )

    def test_malformed_json_and_provider_failure_preserve_production(self) -> None:
        for mode, inner in (
            ("invalid", EditModel(malformed="invalid")),
            ("fenced", EditModel(malformed="fenced")),
            ("trailing", EditModel(malformed="trailing")),
            ("duplicate_key", EditModel(malformed="duplicate_key")),
            ("provider", EditModel(fail_revision=True)),
        ):
            with self.subTest(mode=mode):
                model, _searches, result = self._run(inner=inner)
                receipt = result["content_free_receipt"]
                parent = result["parent_result"]["content_free_receipt"]
                self.assertEqual(model.logical_calls, 4)
                self.assertTrue(parent["revision_failure_present"])
                self.assertEqual(result["prediction"], result["production_prediction"])
                if mode != "provider":
                    self.assertTrue(receipt["projection_failure_present"])
                    self.assertFalse(receipt["edit_response_strict_json"])
                else:
                    self.assertTrue(receipt["provider_failure_present"])

    def test_parent_posteffect_failure_preserves_production(self) -> None:
        inner, _searches, result = self._run(post_effect_failure=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertTrue(receipt["parent_post_effect_failure_present"])
        self.assertTrue(receipt["production_prediction_preserved_on_failure"])
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_privileged_or_budget_drift_fails_before_effect(self) -> None:
        for mode in ("privileged", "budget"):
            inner = EditModel()
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

    def test_receipt_and_parent_tamper_fail_closed(self) -> None:
        _inner, _searches, result = self._run()
        for mode in ("applied", "rejection", "accounting", "launch", "parent"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if mode == "applied":
                receipt["applied_edit_count"] = 0
            elif mode == "rejection":
                receipt["rejection_counts"]["invalid_page_ordinal"] = 1
            elif mode == "accounting":
                receipt["model_edit_count"] += 1
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

    def test_receipt_is_content_free_and_signed_credit_zero(self) -> None:
        _inner, _searches, result = self._run()
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
        self.assertFalse(result["entropy_or_information_gain_assigns_signed_credit"])

    def test_module_is_label_blind_build_only_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25143_quote_attested_cell_edit_runtime.py"
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
