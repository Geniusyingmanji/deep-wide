from __future__ import annotations

import ast
import copy
import hashlib
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
from deepwide_agent import v25349_shared_prefix_grounded_fact_paired_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25119_grounded_target_record_paired_runtime import (  # noqa: E402
    GroundedFrontierSearch,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
    TASK,
    limits,
)


FACT_QUOTE = (
    ".in has TLD Manager 999 in the visible IANA Root Zone Database authority."
)


class FactSearch(GroundedFrontierSearch):
    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        if self._phase == target.FIRST_PHASE:
            for batch in output:
                for item in batch.get("results", []):
                    if "country-0-0" in str(item.get("url") or ""):
                        item["raw_content"] = (
                            "India is the country whose capital is New Delhi and "
                            "currency is INR. " + FACT_QUOTE
                        )
        return output


class PairedFactModel:
    def __init__(
        self,
        *,
        joint: bool,
        bad_quote: bool = False,
        alternate_unexposed: bool = False,
        fail_grounded: bool = False,
    ) -> None:
        self.joint = joint
        self.bad_quote = bad_quote
        self.alternate_unexposed = alternate_unexposed
        self.fail_grounded = fail_grounded
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = self.synthesis_calls = 0
        self.synthesis_users: list[str] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens, json_mode
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
                    "columns": ["provider column must be ignored"],
                    "queries": [
                        "capital New Delhi currency INR country",
                        "New Delhi INR official source",
                        "country domain type",
                        "country TLD manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            if self.fail_grounded:
                raise RuntimeError("synthetic grounded provider failure")
            value = {
                "pivots": ["India"],
                "row_targets": [".in"],
                "authority_terms": ["IANA Root Zone Database"],
                "queries": [
                    "India .in Domain Type IANA",
                    "India .in TLD Manager IANA",
                ],
            }
            if self.joint:
                quote = (
                    ".in has TLD Manager 777 in the visible IANA Root Zone Database authority."
                    if self.bad_quote
                    else FACT_QUOTE
                )
                value["records"] = [
                    {
                        "page_ordinal": 1,
                        "quote": quote,
                        "row_identity": ".in",
                        "fields": [
                            {
                                "column": "TLD Manager",
                                "source_field": "TLD Manager",
                                "value": "777" if self.bad_quote else "999",
                            }
                        ],
                    }
                ]
            text = json.dumps(value)
        else:
            self.synthesis_calls += 1
            self.synthesis_users.append(str(user))
            if "[QUOTE_VERIFIED_RECORD" in user:
                manager = "999"
            elif self.alternate_unexposed:
                manager = "111" if self.synthesis_calls == 1 else "222"
            else:
                manager = "111"
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                f"| .in | country-code | {manager} |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class V25349SharedPrefixGroundedFactPairedRuntimeTests(unittest.TestCase):
    def _wiring(
        self,
        root: Path,
        *,
        joint: bool,
        bad_quote: bool = False,
        alternate_unexposed: bool = False,
        fail_grounded: bool = False,
    ):
        inner = PairedFactModel(
            joint=joint,
            bad_quote=bad_quote,
            alternate_unexposed=alternate_unexposed,
            fail_grounded=fail_grounded,
        )
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            inner,
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
        return inner, budget, model, searches

    def _run(
        self,
        *,
        joint: bool,
        bad_quote: bool = False,
        alternate_unexposed: bool = False,
        fail_grounded: bool = False,
        arm_order=None,
    ):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(
                root,
                joint=joint,
                bad_quote=bad_quote,
                alternate_unexposed=alternate_unexposed,
                fail_grounded=fail_grounded,
            )
            result = target.run_paired_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                arm_order=arm_order,
                monotonic=time.monotonic,
            )
        return inner, budget, searches, target.validate_result(result)

    def test_verified_fact_is_attributable_with_shared_4_14_4_cap(self) -> None:
        inner, budget, searches, result = self._run(
            joint=True, arm_order=target.ARMS
        )
        receipt = result["content_free_receipt"]
        fact = receipt["grounded_fact_receipt"]
        physical = budget.receipt()
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertLessEqual(receipt["physical_fetch_count"], 14)
        self.assertEqual(receipt["physical_model_forward_count"], 4)
        self.assertEqual(receipt["model_provider_request_count"], 4)
        self.assertEqual(receipt["model_provider_attempt_count"], 4)
        self.assertEqual(physical["model_rejected_count"], 0)
        self.assertTrue(receipt["first_wave_completed"])
        self.assertTrue(receipt["second_wave_completed"])
        self.assertTrue(receipt["grounded_plan_strategy_applied"])
        self.assertTrue(receipt["candidate_production_prompt_changed"])
        self.assertEqual(fact["verified_record_count"], 1)
        self.assertEqual(fact["verified_field_count"], 1)
        self.assertEqual(fact["additional_model_call_count"], 0)
        self.assertTrue(result["prediction_changed"])
        self.assertTrue(result["attributable_prediction_change"])
        self.assertFalse(result["unattributable_prediction_change"])
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])
        self.assertEqual(
            searches[target.FIRST_PHASE]._inner_search.calls, 1
        )
        self.assertEqual(
            receipt["control_production_prompt_characters"],
            receipt["candidate_production_prompt_characters"],
        )

    def test_invalid_quote_is_no_treatment_and_no_prediction_change(self) -> None:
        inner, _budget, _searches, result = self._run(
            joint=True, bad_quote=True
        )
        receipt = result["content_free_receipt"]
        fact = receipt["grounded_fact_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(fact["verified_record_count"], 0)
        self.assertEqual(fact["rendered_record_count"], 0)
        self.assertFalse(result["candidate_production_prompt_changed"])
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(result["attributable_prediction_change"])
        self.assertFalse(result["unattributable_prediction_change"])
        self.assertEqual(
            result["predictions"][target.CONTROL_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )
        self.assertEqual(inner.synthesis_users[0], inner.synthesis_users[1])

    def test_grounded_provider_failure_is_terminal_no_treatment(self) -> None:
        inner, budget, _searches, result = self._run(
            joint=False, fail_grounded=True
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(
            receipt["failure_types"]["grounded_plan"], "RuntimeError"
        )
        self.assertFalse(receipt["grounded_plan_model_call_success"])
        self.assertFalse(result["candidate_production_prompt_changed"])
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(result["attributable_prediction_change"])
        self.assertEqual(budget.receipt()["model_admitted_count"], 4)

    def test_reversed_arm_order_preserves_treatment_attribution(self) -> None:
        _inner, _budget, _searches, result = self._run(
            joint=True, arm_order=target.ARMS[::-1]
        )
        self.assertEqual(
            result["content_free_receipt"]["first_synthesis_arm"],
            target.CANDIDATE_ARM,
        )
        self.assertIn("111", result["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["predictions"][target.CANDIDATE_ARM])
        self.assertTrue(result["attributable_prediction_change"])
        self.assertFalse(result["unattributable_prediction_change"])

    def test_unexposed_order_difference_is_unattributable(self) -> None:
        _inner, _budget, _searches, result = self._run(
            joint=False,
            alternate_unexposed=True,
            arm_order=target.ARMS,
        )
        self.assertFalse(result["candidate_production_prompt_changed"])
        self.assertTrue(result["prediction_changed"])
        self.assertFalse(result["attributable_prediction_change"])
        self.assertTrue(result["unattributable_prediction_change"])

    def test_privileged_boundary_fails_before_any_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root, joint=True)
            with self.assertRaises(ValueError):
                target.run_paired_task(
                    {**TASK, "question_type": "forbidden"},
                    model=model,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                )
        self.assertEqual(inner.logical_calls, 0)
        self.assertTrue(
            all(search._inner_search.calls == 0 for search in searches.values())
        )
        physical = budget.receipt()
        self.assertEqual(physical["query_admitted_count"], 0)
        self.assertEqual(physical["fetch_admitted_count"], 0)
        self.assertEqual(physical["model_admitted_count"], 0)

    def test_resealed_nested_counter_credit_or_prediction_tamper_fails(self) -> None:
        _inner, _budget, _searches, result = self._run(joint=True)
        for kind in ("fact", "counter", "credit", "prediction"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if kind == "fact":
                fact = receipt["grounded_fact_receipt"]
                fact["additional_model_call_count"] = 1
                fact.pop("receipt_payload_sha256")
                fact["receipt_payload_sha256"] = payload_sha256(fact)
            elif kind == "counter":
                receipt["model_provider_request_count"] -= 1
            elif kind == "credit":
                receipt["positive_signed_credit_count"] = 1
            else:
                changed["predictions"][target.CANDIDATE_ARM] += "x"
                changed["prediction_sha256"][target.CANDIDATE_ARM] = hashlib.sha256(
                    changed["predictions"][target.CANDIDATE_ARM].encode()
                ).hexdigest()
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_effect_import(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25349_shared_prefix_grounded_fact_paired_runtime.py"
        )
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        for forbidden in (
            "run_official_eval_local",
            "api_key",
            "os.environ",
            "target/main",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
