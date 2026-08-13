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

from deepwide_agent import v25232_header_totality_shadow_runtime as fixture_parent  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as control  # noqa: E402
from deepwide_agent import v25347_checkpoint_grounded_fact_runtime as target  # noqa: E402
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
        if self._phase == target.sparse.FIRST_PHASE:
            for batch in output:
                for item in batch.get("results", []):
                    if "country-0-0" in str(item.get("url") or ""):
                        item["raw_content"] = (
                            "India is the country whose capital is New Delhi and "
                            "currency is INR. " + FACT_QUOTE
                        )
        return output


class BootstrapModel:
    def __init__(self, *, joint: bool, bad_quote: bool = False) -> None:
        self.joint = joint
        self.bad_quote = bad_quote
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "columns": ["ignored"],
                    "queries": [
                        QUESTION,
                        "New Delhi INR official source",
                        "country domain type",
                        "country TLD manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
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
            marker = "[QUOTE_VERIFIED_RECORD" in user
            manager = "999" if marker else "111"
            text = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                f"| .in | country-code | {manager} |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class V25347CheckpointGroundedFactRuntimeTests(unittest.TestCase):
    def _wiring(self, root: Path, *, joint: bool, bad_quote: bool = False):
        inner = BootstrapModel(joint=joint, bad_quote=bad_quote)
        budget = cap.PhysicalEffectBudget()
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
        model = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                FactSearch(QUESTION, phase), budget, phase=phase
            )
            for phase in fixture_parent.PHASES
        }
        return inner, budget, model, searches

    def _run(self, *, joint: bool, bad_quote: bool = False):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(
                root, joint=joint, bad_quote=bad_quote
            )
            result, stage = target.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, target.validate_result(result), target.validate_stage_receipt(stage)

    def _run_control(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root, joint=False)
            result, stage = control.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        return inner, control.validate_result(result), control.validate_stage_receipt(stage)

    def test_parent_only_output_matches_checkpoint_control(self) -> None:
        control_inner, baseline, _baseline_stage = self._run_control()
        inner, result, stage = self._run(joint=False)
        receipt = result["content_free_receipt"]
        proxy = receipt["grounded_fact_proxy_receipt"]
        self.assertEqual(inner.logical_calls, control_inner.logical_calls)
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertEqual(result["prediction_kind"], baseline["prediction_kind"])
        self.assertEqual(result["cost"], baseline["cost"])
        self.assertFalse(receipt["candidate_production_prompt_changed"])
        self.assertEqual(proxy["additional_model_call_count"], 0)
        self.assertEqual(stage["checkpoint_failure_count"], 0)

    def test_joint_verified_fact_changes_prediction_with_three_calls(self) -> None:
        inner, result, stage = self._run(joint=True)
        receipt = result["content_free_receipt"]
        proxy = receipt["grounded_fact_proxy_receipt"]
        component = proxy["bootstrap_component_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["provider_forward_count"], 3)
        self.assertEqual(receipt["model_provider_request_count"], 3)
        self.assertEqual(receipt["model_provider_attempt_count"], 3)
        self.assertEqual(receipt["physical_model_forward_count"], 3)
        self.assertEqual(receipt["revision_provider_forward_count"], 0)
        self.assertTrue(receipt["candidate_production_prompt_changed"])
        self.assertEqual(component["verified_record_count"], 1)
        self.assertEqual(component["verified_field_count"], 1)
        self.assertEqual(component["additional_model_call_count"], 0)
        self.assertIn("999", result["prediction"])
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertIsNotNone(result["production_checkpoint"])
        self.assertEqual(stage["checkpoint_failure_count"], 0)

    def test_invalid_quote_is_parent_prompt_noop(self) -> None:
        inner, result, _stage = self._run(joint=True, bad_quote=True)
        proxy = result["content_free_receipt"]["grounded_fact_proxy_receipt"]
        component = proxy["bootstrap_component_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertFalse(proxy["candidate_production_prompt_changed"])
        self.assertEqual(component["verified_record_count"], 0)
        self.assertEqual(component["rendered_record_count"], 0)
        self.assertIn("111", result["prediction"])

    def test_post_checkpoint_failure_preserves_treated_prediction(self) -> None:
        _inner, baseline, _stage = self._run(joint=True)
        with mock.patch.object(
            control, "_build_result", side_effect=ValueError("hidden build detail")
        ):
            inner, result, stage = self._run(joint=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(result["prediction"], baseline["prediction"])
        self.assertIn("999", result["prediction"])
        self.assertTrue(receipt["candidate_production_prompt_changed"])
        self.assertTrue(receipt["checkpoint_recovery_event_present"])
        self.assertEqual(
            receipt["checkpoint_recovery_disposition"],
            "validated_production_preserved_after_post_checkpoint_failure",
        )
        self.assertEqual(result["inner_checkpoint_result_role"], control.RECOVERY_ROLE)
        self.assertEqual(stage["checkpoint_failure_count"], 1)
        self.assertNotIn("hidden build detail", str(result))

    def test_privileged_boundary_fails_before_any_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner, budget, model, searches = self._wiring(root, joint=True)
            with self.assertRaises(ValueError):
                target.run_task(
                    {**TASK, "question_type": "forbidden"},
                    model=model,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        self.assertEqual(inner.logical_calls, 0)
        self.assertTrue(all(search.calls == 0 for search in searches.values()))

    def test_resealed_result_proxy_stage_or_credit_tamper_fails(self) -> None:
        _inner, result, stage = self._run(joint=True)
        for kind in (
            "proxy", "result", "credit", "requests", "attempts", "stage",
            "stage_proxy",
        ):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if kind == "proxy":
                proxy = receipt["grounded_fact_proxy_receipt"]
                proxy["additional_model_call_count"] = 1
                proxy.pop("receipt_payload_sha256")
                proxy["receipt_payload_sha256"] = payload_sha256(proxy)
            elif kind == "result":
                changed["prediction"] += "x"
                changed["prediction_sha256"] = __import__("hashlib").sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            elif kind == "credit":
                receipt["positive_signed_credit_count"] = 1
            elif kind == "requests":
                receipt["model_provider_request_count"] -= 1
            elif kind == "attempts":
                receipt["model_provider_attempt_count"] += 1
            elif kind in {"stage", "stage_proxy"}:
                changed_stage = copy.deepcopy(stage)
                if kind == "stage":
                    changed_stage["candidate_production_prompt_changed"] = False
                else:
                    stage_proxy = changed_stage["grounded_fact_proxy_receipt"]
                    stage_proxy["candidate_production_prompt_changed"] = False
                    stage_proxy.pop("receipt_payload_sha256")
                    stage_proxy["receipt_payload_sha256"] = payload_sha256(
                        stage_proxy
                    )
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = payload_sha256(
                    changed_stage
                )
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_outer_envelope_does_not_persist_legacy_parent_or_prompt_claim(self) -> None:
        _inner, result, _stage = self._run(joint=True)
        self.assertNotIn("parent_result", result)
        self.assertNotIn("checkpoint_runtime_result", result)
        def without_seals(value):
            if isinstance(value, dict):
                return {
                    key: without_seals(item)
                    for key, item in value.items()
                    if not key.endswith("sha256")
                }
            if isinstance(value, list):
                return [without_seals(item) for item in value]
            return value

        encoded = json.dumps(
            without_seals(result["content_free_receipt"]),
            ensure_ascii=False,
        )
        for forbidden in (
            "New Delhi", "India", ".in", "999", "https://", TASK["opaque_id"]
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertTrue(
            result["content_free_receipt"][
                "legacy_prompt_unchanged_claim_not_reexported"
            ]
        )

    def test_runtime_is_label_blind_and_has_no_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25347_checkpoint_grounded_fact_runtime.py"
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
                    "category", "question_type", "task_category", "split",
                    "ground_truth", "gold", "answer_key", "score", "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in (
            "os", "pathlib", "subprocess", "requests", "httpx", "socket", "urllib"
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged, [])
        for forbidden in ("official_eval", "api_key", "os.environ", "target/main"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
