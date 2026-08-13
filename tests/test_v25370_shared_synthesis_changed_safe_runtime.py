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

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
    TASK,
    limits,
)
from test_v25349_shared_prefix_grounded_fact_paired_runtime import (  # noqa: E402
    FACT_QUOTE,
    FactSearch,
)


class SharedBaseModel:
    def __init__(
        self,
        *,
        verified_value: str = "999",
        synthesis_value: str = "111",
        include_bad_field: bool = False,
        invalid_quote: bool = False,
        fail_synthesis: bool = False,
    ) -> None:
        self.verified_value = verified_value
        self.synthesis_value = synthesis_value
        self.include_bad_field = include_bad_field
        self.invalid_quote = invalid_quote
        self.fail_synthesis = fail_synthesis
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.synthesis_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["provider schema ignored"],
                    "queries": [
                        "capital New Delhi currency INR country",
                        "New Delhi INR official source",
                        "country domain type",
                        "country TLD manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            fields = [
                {
                    "column": "TLD Manager",
                    "source_field": "TLD Manager",
                    "value": self.verified_value,
                }
            ]
            if self.include_bad_field:
                fields.append(
                    {
                        "column": "Type",
                        "source_field": "Unsupported label",
                        "value": "country-code",
                    }
                )
            quote = (
                ".in has TLD Manager 777 in an absent authority passage."
                if self.invalid_quote
                else FACT_QUOTE
            )
            text = json.dumps(
                {
                    "pivots": ["India"],
                    "row_targets": [".in"],
                    "authority_terms": ["IANA Root Zone Database"],
                    "queries": [
                        "India .in Domain Type IANA",
                        "India .in TLD Manager IANA",
                    ],
                    "records": [
                        {
                            "page_ordinal": 1,
                            "quote": quote,
                            "row_identity": ".in",
                            "fields": fields,
                        }
                    ],
                }
            )
        else:
            self.synthesis_calls += 1
            if self.fail_synthesis:
                raise RuntimeError("synthetic base synthesis failure")
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                f"| .in | country-code | {self.synthesis_value} |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class V25370SharedSynthesisChangedSafeRuntimeTests(unittest.TestCase):
    def _run(self, inner=None):
        chosen = inner or SharedBaseModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                chosen,
                slot_directory=slots,
                output_root=root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            budget = cap.PhysicalEffectBudget()
            model = cap.HardCappedModelLimiter(bounded, budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    FactSearch(QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            result = target.run_paired_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return chosen, budget, searches, target.validate_result(result)

    def test_one_shared_synthesis_then_deterministic_edit_is_attributable(self) -> None:
        inner, budget, searches, value = self._run()
        receipt = value["content_free_receipt"]
        edit = receipt["changed_safe_edit_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(inner.synthesis_calls, 1)
        self.assertEqual(budget.receipt()["model_admitted_count"], 3)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)
        self.assertEqual(receipt["physical_model_forward_count"], 3)
        self.assertEqual(edit["verified_field_count"], 1)
        self.assertEqual(edit["changed_safe_coordinate_count"], 1)
        self.assertIn("111", value["predictions"][target.CONTROL_ARM])
        self.assertIn("999", value["predictions"][target.CANDIDATE_ARM])
        self.assertTrue(value["prediction_changed"])
        self.assertTrue(value["attributable_prediction_change"])
        self.assertFalse(value["unattributable_prediction_change"])
        self.assertEqual(searches[target.FIRST_PHASE]._inner_search.calls, 1)

    def test_matching_verified_value_is_identity_without_second_sampling(self) -> None:
        inner, budget, _searches, value = self._run(
            SharedBaseModel(verified_value="999", synthesis_value="999")
        )
        receipt = value["content_free_receipt"]
        edit = receipt["changed_safe_edit_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(inner.synthesis_calls, 1)
        self.assertEqual(budget.receipt()["model_admitted_count"], 3)
        self.assertEqual(edit["unchanged_verified_coordinate_count"], 1)
        self.assertEqual(edit["changed_safe_coordinate_count"], 0)
        self.assertTrue(receipt["candidate_identity_handoff"])
        self.assertFalse(value["prediction_changed"])
        self.assertEqual(
            value["predictions"][target.CONTROL_ARM],
            value["predictions"][target.CANDIDATE_ARM],
        )

    def test_partial_field_keeps_good_field_and_omits_bad_field(self) -> None:
        inner, _budget, _searches, value = self._run(
            SharedBaseModel(include_bad_field=True)
        )
        edit = value["content_free_receipt"]["changed_safe_edit_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(edit["parsed_field_count"], 2)
        self.assertEqual(edit["verified_field_count"], 1)
        self.assertEqual(edit["changed_safe_coordinate_count"], 1)
        self.assertTrue(value["attributable_prediction_change"])

    def test_invalid_quote_is_verified_noop(self) -> None:
        inner, _budget, _searches, value = self._run(
            SharedBaseModel(invalid_quote=True)
        )
        edit = value["content_free_receipt"]["changed_safe_edit_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(edit["verified_field_count"], 0)
        self.assertFalse(value["prediction_changed"])
        self.assertFalse(value["attributable_prediction_change"])

    def test_base_synthesis_failure_uses_canonical_identity_fallback(self) -> None:
        inner, budget, _searches, value = self._run(
            SharedBaseModel(fail_synthesis=True)
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(inner.synthesis_calls, 1)
        self.assertEqual(budget.receipt()["model_admitted_count"], 3)
        self.assertFalse(receipt["base_synthesis_model_success"])
        self.assertFalse(receipt["base_table_exact_canonical"])
        self.assertEqual(receipt["base_normalizer_status"], "unrecoverable")
        self.assertEqual(receipt["failure_types"]["synthesis"], "RuntimeError")
        self.assertTrue(receipt["candidate_identity_handoff"])
        self.assertFalse(value["prediction_changed"])
        self.assertFalse(value["attributable_prediction_change"])

    def test_privileged_boundary_fails_before_any_effect(self) -> None:
        chosen = SharedBaseModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                chosen,
                slot_directory=slots,
                output_root=root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            budget = cap.PhysicalEffectBudget()
            model = cap.HardCappedModelLimiter(bounded, budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    FactSearch(QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_paired_task(
                    {**TASK, "question_type": "forbidden"},
                    model=model,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                )
        self.assertEqual(chosen.logical_calls, 0)
        self.assertEqual(budget.receipt()["model_admitted_count"], 0)
        self.assertTrue(
            all(search._inner_search.calls == 0 for search in searches.values())
        )

    def test_resealed_editor_counter_credit_or_prediction_tamper_fails(self) -> None:
        _inner, _budget, _searches, value = self._run()
        for kind in ("editor", "counter", "credit", "prediction"):
            changed = copy.deepcopy(value)
            receipt = changed["content_free_receipt"]
            if kind == "editor":
                nested = receipt["changed_safe_edit_receipt"]
                nested["changed_safe_coordinate_count"] += 1
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            elif kind == "counter":
                receipt["physical_model_forward_count"] += 1
            elif kind == "credit":
                receipt["positive_signed_credit_count"] = 1
            else:
                changed["predictions"][target.CANDIDATE_ARM] += "x"
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25370_shared_synthesis_changed_safe_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
