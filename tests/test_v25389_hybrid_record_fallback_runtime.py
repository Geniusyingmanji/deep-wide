from __future__ import annotations

import ast
import copy
import json
import re
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as frozen_parent  # noqa: E402
from deepwide_agent import v25389_hybrid_record_fallback_runtime as target  # noqa: E402
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
from test_v25375_schema_total_changed_safe_runtime import (  # noqa: E402
    ONE_COLUMN_QUESTION,
)


_EVIDENCE_RECORD = re.compile(
    r"(?ms)^\[E(?P<ordinal>[0-9]{4})\] kind=fetched_page\n"
    r"(?P<body>.*?)(?=\n\n\[E[0-9]{4}\] kind=fetched_page\n|\Z)"
)


class HybridModel:
    def __init__(
        self,
        *,
        grounded_records: bool = True,
        grounded_invalid: bool = False,
        joint_mode: str = "empty",
        table_value: str = "111",
        one_column: bool = False,
    ) -> None:
        if joint_mode not in {"empty", "valid", "invalid"}:
            raise ValueError(joint_mode)
        self.grounded_records = grounded_records
        self.grounded_invalid = grounded_invalid
        self.joint_mode = joint_mode
        self.table_value = table_value
        self.one_column = one_column
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def _joint_ordinal(self, user: str) -> int:
        for match in _EVIDENCE_RECORD.finditer(user):
            if FACT_QUOTE in match.group("body"):
                return int(match.group("ordinal"))
        raise AssertionError("joint evidence omitted first-wave quote")

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, max_output_tokens
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
                    "columns": ["ignored"],
                    "queries": [
                        "capital New Delhi currency INR country",
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
            if self.grounded_records:
                quote = (
                    ".in has TLD Manager 777 in an absent first-wave passage."
                    if self.grounded_invalid
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
                                "value": "777" if self.grounded_invalid else "999",
                            }
                        ],
                    }
                ]
            text = json.dumps(value)
        else:
            if self.one_column:
                table = "| Result |\n|---|\n| India |"
                records = []
            else:
                table = (
                    "| Domain | Type | TLD Manager |\n"
                    "|---|---|---|\n"
                    f"| .in | country-code | {self.table_value} |"
                )
                if self.joint_mode == "empty":
                    records = []
                else:
                    ordinal = self._joint_ordinal(str(user))
                    records = [
                        {
                            "page_ordinal": ordinal,
                            "quote": (
                                FACT_QUOTE
                                if self.joint_mode == "valid"
                                else ".in has TLD Manager 888 in an absent joint passage."
                            ),
                            "row_identity": ".in",
                            "fields": [
                                {
                                    "column": "TLD Manager",
                                    "source_field": "TLD Manager",
                                    "value": (
                                        "999" if self.joint_mode == "valid" else "888"
                                    ),
                                }
                            ],
                        }
                    ]
            if not json_mode:
                raise AssertionError("hybrid synthesis must request JSON mode")
            text = json.dumps({"table": table, "records": records})
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def run(model: HybridModel, *, question: str = QUESTION):
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


class V25389HybridRecordFallbackRuntimeTests(unittest.TestCase):
    def test_empty_joint_uses_valid_grounded_record_and_changes_base(self) -> None:
        model = HybridModel(joint_mode="empty")
        result, stage, budget = run(model)
        receipt = result["hybrid_record_fallback_receipt"]
        parent = result["private_parent_result"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(receipt["record_source"], "grounded")
        self.assertEqual(receipt["grounded_raw_record_count"], 1)
        self.assertEqual(receipt["joint_raw_record_count"], 0)
        self.assertTrue(receipt["grounded_fallback_selected"])
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["changed_safe_coordinate_count"], 1)
        self.assertIn("111", parent["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["prediction"])
        self.assertTrue(result["prediction_changed"])
        self.assertTrue(result["attributable_prediction_change"])
        self.assertFalse(stage["failure_present"])

    def test_nonempty_invalid_joint_preempts_valid_grounded_without_fallthrough(self) -> None:
        result, _stage, budget = run(HybridModel(joint_mode="invalid"))
        receipt = result["hybrid_record_fallback_receipt"]
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(receipt["record_source"], "joint")
        self.assertEqual(receipt["grounded_raw_record_count"], 1)
        self.assertEqual(receipt["joint_raw_record_count"], 1)
        self.assertTrue(receipt["joint_nonempty_preempts_grounded"])
        self.assertFalse(receipt["grounded_fallback_selected"])
        self.assertEqual(receipt["verified_record_count"], 0)
        self.assertEqual(receipt["changed_safe_coordinate_count"], 0)
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(result["attributable_prediction_change"])

    def test_nonempty_valid_joint_has_priority_and_changes_base(self) -> None:
        result, _stage, budget = run(HybridModel(joint_mode="valid"))
        receipt = result["hybrid_record_fallback_receipt"]
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(receipt["record_source"], "joint")
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["changed_safe_coordinate_count"], 1)
        self.assertTrue(result["prediction_changed"])

    def test_invalid_grounded_and_no_source_are_identity_noops(self) -> None:
        cases = (
            HybridModel(joint_mode="empty", grounded_invalid=True),
            HybridModel(joint_mode="empty", grounded_records=False),
        )
        for model in cases:
            with self.subTest(grounded=model.grounded_records):
                result, _stage, budget = run(model)
                receipt = result["hybrid_record_fallback_receipt"]
                self.assertEqual(budget["model_admitted_count"], 3)
                self.assertFalse(result["prediction_changed"])
                self.assertEqual(receipt["changed_safe_coordinate_count"], 0)
        none, _stage, _budget = run(
            HybridModel(joint_mode="empty", grounded_records=False)
        )
        self.assertEqual(
            none["hybrid_record_fallback_receipt"]["record_source"], "none"
        )

    def test_one_column_schema_is_model_generated_identity(self) -> None:
        model = HybridModel(
            grounded_records=False, joint_mode="empty", one_column=True
        )
        result, stage, budget = run(model, question=ONE_COLUMN_QUESTION)
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertTrue(
            result["schema_totality_receipt"][
                "single_column_changed_safe_identity_noop"
            ]
        )
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(stage["failure_present"])

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = HybridModel()
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
                    {**TASK, "question_type": "forbidden"},
                    model=outer,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        self.assertEqual(model.logical_calls, 0)
        self.assertEqual(budget.receipt()["model_admitted_count"], 0)

    def test_mixed_concurrency_does_not_mutate_parent_globals(self) -> None:
        original_projector = frozen_parent.query_parent
        original_verifier = frozen_parent.verifier
        original_editor = frozen_parent.editor
        cases = [
            HybridModel(joint_mode="empty"),
            HybridModel(joint_mode="valid"),
            HybridModel(joint_mode="invalid"),
            HybridModel(joint_mode="empty", grounded_records=False),
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda model: run(model)[0], cases))
        self.assertEqual(
            [value["prediction_changed"] for value in outputs],
            [True, True, False, False],
        )
        self.assertIs(frozen_parent.query_parent, original_projector)
        self.assertIs(frozen_parent.verifier, original_verifier)
        self.assertIs(frozen_parent.editor, original_editor)

    def test_resealed_source_parent_prediction_or_credit_tamper_fails(self) -> None:
        result, _stage, _budget = run(HybridModel(joint_mode="empty"))
        for kind in ("source", "parent", "prediction", "credit"):
            changed = copy.deepcopy(result)
            receipt = changed["hybrid_record_fallback_receipt"]
            if kind == "source":
                receipt["record_source"] = "joint"
            elif kind == "parent":
                changed["private_parent_result"]["changed_safe_coordinate_count"] += 1
                changed["private_parent_result"].pop("result_payload_sha256")
                changed["private_parent_result"]["result_payload_sha256"] = payload_sha256(
                    changed["private_parent_result"]
                )
            elif kind == "prediction":
                changed["prediction"] += "x"
            else:
                receipt["positive_signed_credit_count"] = 1
            if kind in {"source", "credit"}:
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25389_hybrid_record_fallback_runtime.py"
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
