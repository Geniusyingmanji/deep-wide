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
from deepwide_agent import v25395_visible_membership_synthesis_runtime as frozen  # noqa: E402
from deepwide_agent import v25401_grounded_record_membership_runtime as target  # noqa: E402
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
    FactSearch,
)
from test_v25395_visible_membership_synthesis_runtime import (  # noqa: E402
    MEMBERSHIP_QUESTION,
)


IN_QUOTE = ".in has TLD Manager 999 in the visible public authority."
DE_QUOTE = ".de has TLD Manager 888 in the visible public authority."


class DualIdentitySearch(FactSearch):
    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        for batch in output:
            for item in batch.get("results", []):
                item["raw_content"] = IN_QUOTE + " " + DE_QUOTE
        return output


class GroundedMembershipModel:
    def __init__(self, *, ignore_grounded_constraint: bool = False) -> None:
        self.ignore_grounded_constraint = ignore_grounded_constraint
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.systems: list[str] = []
        self.users: list[str] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        self.systems.append(str(system))
        self.users.append(str(user))
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": [
                        "public authority in uk domain",
                        "public authority domain managers",
                        "in domain type manager",
                        "uk domain type manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            constrained = (
                "VISIBLE RECORD MEMBERSHIP CONSTRAINT:" in str(system)
                and not self.ignore_grounded_constraint
            )
            identity = ".in" if constrained else ".de"
            quote = IN_QUOTE if constrained else DE_QUOTE
            value = "999" if constrained else "888"
            text = json.dumps(
                {
                    "pivots": [identity],
                    "row_targets": [identity],
                    "authority_terms": ["public authority"],
                    "queries": [
                        f"{identity} Domain Type public authority",
                        f"{identity} TLD Manager public authority",
                    ],
                    "records": [
                        {
                            "page_ordinal": 1,
                            "quote": quote,
                            "row_identity": identity,
                            "fields": [
                                {
                                    "column": "TLD Manager",
                                    "source_field": "TLD Manager",
                                    "value": value,
                                }
                            ],
                        }
                    ],
                }
            )
        else:
            if not json_mode:
                raise AssertionError("third call must request JSON mode")
            if "VISIBLE ROW MEMBERSHIP CONSTRAINT:" in str(user):
                table = (
                    "| Domain | Type | TLD Manager |\n"
                    "|---|---|---|\n"
                    "| .in | country-code | 111 |\n"
                    "| .uk | country-code | 222 |"
                )
            else:
                table = (
                    "| Domain | Type | TLD Manager |\n"
                    "|---|---|---|\n"
                    "| .in | country-code | 111 |"
                )
            text = json.dumps({"table": table, "records": []})
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def run_runtime(module, model: GroundedMembershipModel, *, question: str):
    task = {"opaque_id": TASK["opaque_id"], "question": question}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        root = Path(raw)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                DualIdentitySearch(question, phase), budget, phase=phase
            )
            for phase in module.PHASES
        }
        result, stage = module.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return result, stage, cap.validate_budget_receipt(budget.receipt())


class V25401GroundedRecordMembershipRuntimeTests(unittest.TestCase):
    def test_constraint_converts_outside_record_to_visible_member(self) -> None:
        model = GroundedMembershipModel()
        result, stage, budget = run_runtime(
            target, model, question=MEMBERSHIP_QUESTION
        )
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        receipt = checked["grounded_record_membership_receipt"]
        membership_parent = checked["private_parent_result"]
        hybrid = membership_parent["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertIn(
            "VISIBLE RECORD MEMBERSHIP CONSTRAINT:", model.systems[1]
        )
        self.assertEqual(receipt["grounded_raw_record_count"], 1)
        self.assertEqual(receipt["grounded_raw_membership_match_count"], 1)
        self.assertEqual(receipt["grounded_raw_membership_mismatch_count"], 0)
        self.assertTrue(receipt["all_grounded_raw_records_membership_aligned"])
        self.assertEqual(hybrid["missing_row_rejected_field_count"], 0)
        self.assertEqual(hybrid["changed_safe_coordinate_count"], 1)
        self.assertTrue(checked["prediction_changed"])
        self.assertIn("999", checked["prediction"])

    def test_parent_without_grounded_constraint_exposes_missing_row(self) -> None:
        model = GroundedMembershipModel()
        parent_result, _stage, budget = run_runtime(
            frozen, model, question=MEMBERSHIP_QUESTION
        )
        checked = frozen.validate_result(parent_result)
        hybrid = checked["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertNotIn(
            "VISIBLE RECORD MEMBERSHIP CONSTRAINT:", model.systems[1]
        )
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertTrue(
            checked["visible_membership_synthesis_receipt"][
                "base_visible_membership_exact"
            ]
        )
        self.assertEqual(hybrid["missing_row_rejected_field_count"], 1)
        self.assertEqual(hybrid["changed_safe_coordinate_count"], 0)
        self.assertFalse(checked["prediction_changed"])

    def test_provider_violation_is_measured_not_filtered(self) -> None:
        model = GroundedMembershipModel(ignore_grounded_constraint=True)
        result, _stage, _budget = run_runtime(
            target, model, question=MEMBERSHIP_QUESTION
        )
        checked = target.validate_result(result)
        receipt = checked["grounded_record_membership_receipt"]
        hybrid = checked["private_parent_result"]["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(receipt["grounded_raw_membership_match_count"], 0)
        self.assertEqual(receipt["grounded_raw_membership_mismatch_count"], 1)
        self.assertEqual(receipt["grounded_raw_membership_violation_count"], 1)
        self.assertFalse(receipt["all_grounded_raw_records_membership_aligned"])
        self.assertEqual(hybrid["grounded_raw_record_count"], 1)
        self.assertEqual(hybrid["missing_row_rejected_field_count"], 1)
        self.assertFalse(checked["prediction_changed"])

    def test_no_membership_preserves_both_parent_prompts_and_prediction(self) -> None:
        candidate_model = GroundedMembershipModel()
        parent_model = GroundedMembershipModel()
        result, _stage, budget = run_runtime(
            target, candidate_model, question=QUESTION
        )
        parent_result, _parent_stage, _ = run_runtime(
            frozen, parent_model, question=QUESTION
        )
        checked = target.validate_result(result)
        receipt = checked["grounded_record_membership_receipt"]
        self.assertFalse(
            receipt["grounded_record_membership_constraint_applied"]
        )
        self.assertEqual(
            receipt["grounded_record_membership_constraint_characters"], 0
        )
        self.assertEqual(candidate_model.systems, parent_model.systems)
        self.assertEqual(candidate_model.users, parent_model.users)
        self.assertEqual(checked["prediction"], parent_result["prediction"])
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_resealed_receipt_parent_or_credit_tamper_fails(self) -> None:
        result, _stage, _budget = run_runtime(
            target, GroundedMembershipModel(), question=MEMBERSHIP_QUESTION
        )
        for kind in ("receipt", "parent", "credit"):
            changed = copy.deepcopy(result)
            receipt = changed["grounded_record_membership_receipt"]
            if kind == "receipt":
                receipt["grounded_raw_membership_match_count"] = 0
                receipt["grounded_raw_membership_mismatch_count"] = 1
            elif kind == "parent":
                receipt["parent_result_payload_sha256"] = "a" * 64
            else:
                receipt["positive_signed_credit_count"] = 1
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        task = {**TASK, "question_type": "forbidden"}
        model = GroundedMembershipModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                model,
                slot_directory=slots,
                output_root=root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            budget = cap.PhysicalEffectBudget()
            outer = cap.HardCappedModelLimiter(bounded, budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    DualIdentitySearch(QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_task(
                    task,
                    model=outer,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        self.assertEqual(model.logical_calls, 0)
        self.assertEqual(budget.receipt()["model_admitted_count"], 0)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25401_grounded_record_membership_runtime.py"
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
