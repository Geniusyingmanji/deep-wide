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
from deepwide_agent import v25389_hybrid_record_fallback_runtime as frozen  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as target  # noqa: E402
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
from test_v25389_hybrid_record_fallback_runtime import (  # noqa: E402
    HybridModel,
)


MEMBERSHIP_QUESTION = (
    "Use public sources and return one table for the visible rows below.\n"
    "<ENTITIES>\n"
    "1. .in\n"
    "2. .uk\n"
    "</ENTITIES>\n"
    "Columns exactly: Domain | Type | TLD Manager. Preserve row order."
)


class MembershipAwareModel(HybridModel):
    """Omit .in unless the visible membership constraint reaches call three."""

    def __init__(self) -> None:
        super().__init__(joint_mode="empty")
        self.third_user = ""

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls < 2:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        del system, max_output_tokens
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        self.third_user = str(user)
        self.assert_joint_mode = bool(json_mode)
        constrained = "VISIBLE ROW MEMBERSHIP CONSTRAINT:" in self.third_user
        rows = []
        if constrained:
            rows.append("| .in | country-code | 111 |")
        rows.append("| .uk | country-code | 222 |")
        table = (
            "| Domain | Type | TLD Manager |\n"
            "|---|---|---|\n"
            + "\n".join(rows)
        )
        return ModelResult(
            text=json.dumps({"table": table, "records": []}),
            usage={},
            response_id=None,
            attempts=1,
        )


class RecordingHybridModel(HybridModel):
    def __init__(self) -> None:
        super().__init__(joint_mode="empty")
        self.third_user = ""

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 2:
            self.third_user = str(user)
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


def run_target(model: HybridModel, *, question: str):
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
                FactSearch(question, phase), budget, phase=phase
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return (
        target.validate_result(result),
        target.validate_stage_receipt(stage),
        cap.validate_budget_receipt(budget.receipt()),
    )


def run_frozen(model: HybridModel, *, question: str):
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
                FactSearch(question, phase), budget, phase=phase
            )
            for phase in frozen.PHASES
        }
        result, stage = frozen.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return frozen.validate_result(result), frozen.validate_stage_receipt(stage)


class V25395VisibleMembershipSynthesisRuntimeTests(unittest.TestCase):
    def test_strict_visible_membership_grammars_and_ambiguity_fail_closed(self) -> None:
        values, source = target.visible_membership(MEMBERSHIP_QUESTION)
        self.assertEqual(values, (".in", ".uk"))
        self.assertEqual(source, "numbered_or_repeated_tag_vector")
        rfc = (
            "Return exactly the four visible document identities "
            "<RFCS>RFC 9680; RFC 9681; RFC 9682; RFC 9683</RFCS>."
        )
        values, source = target.visible_membership(rfc)
        self.assertEqual(
            values, ("RFC 9680", "RFC 9681", "RFC 9682", "RFC 9683")
        )
        self.assertEqual(source, "plural_inline_tag_vector")
        singular = "Return one row for <PACKAGE>Alpha-Kit</PACKAGE>."
        self.assertEqual(
            target.visible_membership(singular),
            (("Alpha-Kit",), "singular_tag"),
        )
        conflict = MEMBERSHIP_QUESTION + " Also return the row for Germany."
        self.assertEqual(target.visible_membership(conflict), ((), "none"))

    def test_constraint_repairs_pre_synthesis_row_coverage_with_three_calls(self) -> None:
        model = MembershipAwareModel()
        result, stage, budget = run_target(model, question=MEMBERSHIP_QUESTION)
        receipt = result["visible_membership_synthesis_receipt"]
        hybrid = result["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertIn("VISIBLE ROW MEMBERSHIP CONSTRAINT:", model.third_user)
        self.assertEqual(receipt["visible_member_count"], 2)
        self.assertTrue(receipt["membership_constraint_applied"])
        self.assertTrue(receipt["base_visible_membership_exact"])
        self.assertEqual(receipt["base_visible_member_missing_count"], 0)
        self.assertEqual(hybrid["record_source"], "grounded")
        self.assertEqual(hybrid["missing_row_rejected_field_count"], 0)
        self.assertEqual(hybrid["changed_safe_coordinate_count"], 1)
        self.assertTrue(result["prediction_changed"])
        self.assertTrue(result["attributable_prediction_change"])
        self.assertFalse(stage["failure_present"])

    def test_no_membership_is_parent_prompt_and_prediction_identity(self) -> None:
        candidate_model = RecordingHybridModel()
        parent_model = RecordingHybridModel()
        candidate, _stage, candidate_budget = run_target(
            candidate_model, question=QUESTION
        )
        parent_result, _parent_stage = run_frozen(parent_model, question=QUESTION)
        receipt = candidate["visible_membership_synthesis_receipt"]
        self.assertEqual(receipt["membership_source"], "none")
        self.assertFalse(receipt["membership_constraint_applied"])
        self.assertEqual(receipt["membership_constraint_characters"], 0)
        self.assertEqual(candidate["prediction"], parent_result["prediction"])
        self.assertEqual(candidate_model.third_user, parent_model.third_user)
        candidate_hybrid = candidate["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        parent_hybrid = parent_result["hybrid_record_fallback_receipt"]
        for field in (
            "record_source",
            "grounded_raw_record_count",
            "joint_raw_record_count",
            "selected_raw_record_count",
            "verified_record_count",
            "verified_field_count",
            "missing_row_rejected_field_count",
            "unchanged_verified_coordinate_count",
            "changed_safe_coordinate_count",
        ):
            self.assertEqual(candidate_hybrid[field], parent_hybrid[field])
        self.assertEqual(candidate_budget["model_admitted_count"], 3)

    def test_constraint_does_not_create_post_synthesis_rows(self) -> None:
        class IgnoringModel(MembershipAwareModel):
            def complete(self, system, user, *, max_output_tokens, json_mode=False):
                if self.logical_calls < 2:
                    return super().complete(
                        system,
                        user,
                        max_output_tokens=max_output_tokens,
                        json_mode=json_mode,
                    )
                original = self.third_user
                del original
                # Hide the marker only from the synthetic provider behavior;
                # the runtime still sends the real constrained prompt.
                response = super().complete(
                    system,
                    str(user).replace(
                        "VISIBLE ROW MEMBERSHIP CONSTRAINT:",
                        "IGNORED MEMBERSHIP CONSTRAINT:",
                    ),
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
                self.third_user = str(user)
                return response

        result, _stage, _budget = run_target(
            IgnoringModel(), question=MEMBERSHIP_QUESTION
        )
        receipt = result["visible_membership_synthesis_receipt"]
        hybrid = result["private_parent_result"][
            "hybrid_record_fallback_receipt"
        ]
        self.assertTrue(receipt["membership_constraint_applied"])
        self.assertFalse(receipt["base_visible_membership_exact"])
        self.assertEqual(receipt["base_visible_member_missing_count"], 1)
        self.assertEqual(hybrid["missing_row_rejected_field_count"], 1)
        self.assertFalse(result["prediction_changed"])
        self.assertNotIn("| .in |", result["prediction"])

    def test_resealed_membership_parent_or_credit_tamper_fails(self) -> None:
        result, _stage, _budget = run_target(
            MembershipAwareModel(), question=MEMBERSHIP_QUESTION
        )
        for kind in ("membership", "parent", "credit"):
            changed = copy.deepcopy(result)
            receipt = changed["visible_membership_synthesis_receipt"]
            if kind == "membership":
                changed["private_visible_membership"][0] = ".de"
            elif kind == "parent":
                receipt["parent_result_payload_sha256"] = "a" * 64
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
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
        model = HybridModel(joint_mode="empty")
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
                    FactSearch(QUESTION, phase), budget, phase=phase
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
        path = ROOT / "src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py"
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
