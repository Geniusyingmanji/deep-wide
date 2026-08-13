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
from deepwide_agent import v25375_schema_total_changed_safe_runtime as schema_parent  # noqa: E402
from deepwide_agent import v25383_joint_synthesis_changed_safe_runtime as target  # noqa: E402
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
from test_v25375_schema_total_changed_safe_runtime import (  # noqa: E402
    ONE_COLUMN_QUESTION,
)


SECOND_WAVE_QUOTE = (
    "Domain | Type | TLD Manager\n.in | country-code | 999"
)
_EVIDENCE_RECORD = re.compile(
    r"(?ms)^\[E(?P<ordinal>[0-9]{4})\] kind=fetched_page\n"
    r"(?P<body>.*?)(?=\n\n\[E[0-9]{4}\] kind=fetched_page\n|\Z)"
)


class SecondWaveOnlyFactSearch(FactSearch):
    """Put the proposal quote only in pages fetched after grounded planning."""

    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        for batch in output:
            for item in batch.get("results", []):
                if self._phase == target.PHASES[0]:
                    item["raw_content"] = (
                        "India is the country whose capital is New Delhi and "
                        "currency is INR. No registry manager is stated here."
                    )
                else:
                    item["raw_content"] = SECOND_WAVE_QUOTE
        return output


class JointModel:
    def __init__(
        self,
        *,
        table_row: str = ".in",
        table_value: str = "111",
        record_value: str = "999",
        invalid_quote: bool = False,
        malformed_envelope: bool = False,
        grounded_record: bool = True,
        one_column: bool = False,
    ) -> None:
        self.table_row = table_row
        self.table_value = table_value
        self.record_value = record_value
        self.invalid_quote = invalid_quote
        self.malformed_envelope = malformed_envelope
        self.grounded_record = grounded_record
        self.one_column = one_column
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.synthesis_json_modes: list[bool] = []
        self.synthesis_users: list[str] = []

    def _record_ordinal(self, user: str) -> int:
        for match in _EVIDENCE_RECORD.finditer(user):
            if SECOND_WAVE_QUOTE in match.group("body"):
                return int(match.group("ordinal"))
        raise AssertionError("second-wave quote was absent from synthesis evidence")

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
            if self.grounded_record:
                value["records"] = [
                    {
                        "page_ordinal": 1,
                        "quote": "fabricated first-wave quote for .in TLD Manager 777",
                        "row_identity": ".in",
                        "fields": [
                            {
                                "column": "TLD Manager",
                                "source_field": "TLD Manager",
                                "value": "777",
                            }
                        ],
                    }
                ]
            text = json.dumps(value)
        else:
            self.synthesis_json_modes.append(bool(json_mode))
            self.synthesis_users.append(str(user))
            if self.malformed_envelope:
                text = "not-json"
            elif self.one_column:
                text = json.dumps(
                    {
                        "table": "| Result |\n|---|\n| India |",
                        "records": [],
                    }
                )
            else:
                quote = (
                    "fabricated invalid quote for .in TLD Manager 999"
                    if self.invalid_quote
                    else SECOND_WAVE_QUOTE
                )
                ordinal = self._record_ordinal(str(user))
                text = json.dumps(
                    {
                        "table": (
                            "| Domain | Type | TLD Manager |\n"
                            "|---|---|---|\n"
                            f"| {self.table_row} | country-code | "
                            f"{self.table_value} |"
                        ),
                        "records": [
                            {
                                "page_ordinal": ordinal,
                                "quote": quote,
                                "row_identity": ".in",
                                "fields": [
                                    {
                                        "column": "TLD Manager",
                                        "source_field": "TLD Manager",
                                        "value": self.record_value,
                                    }
                                ],
                            }
                        ],
                    }
                )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def run(model: JointModel, *, question: str = QUESTION):
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
                SecondWaveOnlyFactSearch(question, phase), budget, phase=phase
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


class V25383JointSynthesisChangedSafeRuntimeTests(unittest.TestCase):
    def test_second_wave_only_quote_changes_same_response_table(self) -> None:
        model = JointModel()
        result, stage, budget = run(model)
        receipt = result["joint_synthesis_receipt"]
        parent = result["private_parent_result"]
        edit = parent["content_free_receipt"]["changed_safe_edit_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(model.synthesis_json_modes, [True])
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertTrue(receipt["grounded_records_member_present"])
        self.assertEqual(receipt["grounded_records_stripped_count"], 1)
        self.assertGreater(receipt["synthesis_prompt_page_count"], 0)
        self.assertGreater(receipt["verifier_bounded_page_count"], 0)
        self.assertTrue(receipt["joint_envelope_exact"])
        self.assertTrue(receipt["joint_records_armed"])
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 1)
        self.assertEqual(receipt["changed_safe_coordinate_count"], 1)
        self.assertEqual(edit["missing_row_rejected_field_count"], 0)
        self.assertIn("111", parent["predictions"][target.CONTROL_ARM])
        self.assertIn("999", result["prediction"])
        self.assertTrue(result["prediction_changed"])
        self.assertTrue(result["attributable_prediction_change"])
        self.assertFalse(stage["failure_present"])
        self.assertIn("QUOTE-ELIGIBLE SAME-FORWARD", model.synthesis_users[0])

    def test_invalid_quote_absent_row_and_same_value_are_noops(self) -> None:
        cases = {
            "invalid_quote": JointModel(invalid_quote=True),
            "absent_row": JointModel(table_row=".us"),
            "same_value": JointModel(table_value="999"),
        }
        for name, model in cases.items():
            with self.subTest(name=name):
                result, _stage, budget = run(model)
                receipt = result["joint_synthesis_receipt"]
                self.assertEqual(budget["model_admitted_count"], 3)
                self.assertFalse(result["prediction_changed"])
                self.assertFalse(result["attributable_prediction_change"])
                self.assertEqual(receipt["changed_safe_coordinate_count"], 0)
        absent, _stage, _budget = run(JointModel(table_row=".us"))
        self.assertEqual(
            absent["joint_synthesis_receipt"]["missing_row_rejected_field_count"],
            1,
        )
        same, _stage, _budget = run(JointModel(table_value="999"))
        self.assertEqual(
            same["joint_synthesis_receipt"]["unchanged_verified_coordinate_count"],
            1,
        )

    def test_malformed_envelope_is_total_identity_fallback(self) -> None:
        model = JointModel(malformed_envelope=True)
        result, stage, budget = run(model)
        receipt = result["joint_synthesis_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertFalse(receipt["joint_envelope_exact"])
        self.assertFalse(receipt["joint_records_armed"])
        self.assertFalse(receipt["base_synthesis_model_success"])
        self.assertEqual(result["prediction_kind"], "fallback")
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(stage["failure_present"])

    def test_one_column_schema_is_joint_model_generated_identity(self) -> None:
        model = JointModel(one_column=True)
        result, stage, budget = run(model, question=ONE_COLUMN_QUESTION)
        receipt = result["joint_synthesis_receipt"]
        schema = result["schema_totality_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertTrue(schema["single_column_changed_safe_identity_noop"])
        self.assertTrue(receipt["joint_envelope_exact"])
        self.assertTrue(receipt["joint_table_normalizable"])
        self.assertFalse(receipt["joint_records_armed"])
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(stage["failure_present"])

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = JointModel()
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
                    SecondWaveOnlyFactSearch(QUESTION, phase),
                    budget,
                    phase=phase,
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
        receipt = budget.receipt()
        self.assertEqual(receipt["query_admitted_count"], 0)
        self.assertEqual(receipt["fetch_admitted_count"], 0)
        self.assertEqual(receipt["model_admitted_count"], 0)

    def test_mixed_concurrency_does_not_mutate_parent_globals(self) -> None:
        original_projector = frozen_parent.query_parent
        original_verifier = frozen_parent.verifier
        original_editor = frozen_parent.editor
        cases = [
            JointModel(table_value="111"),
            JointModel(table_value="999"),
            JointModel(invalid_quote=True),
            JointModel(table_row=".us"),
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda model: run(model)[0], cases))
        self.assertEqual([value["prediction_changed"] for value in outputs], [True, False, False, False])
        self.assertIs(frozen_parent.query_parent, original_projector)
        self.assertIs(frozen_parent.verifier, original_verifier)
        self.assertIs(frozen_parent.editor, original_editor)

    def test_resealed_joint_parent_prediction_or_credit_tamper_fails(self) -> None:
        result, _stage, _budget = run(JointModel())
        for kind in ("joint", "parent", "prediction", "credit"):
            changed = copy.deepcopy(result)
            if kind == "joint":
                joint = changed["joint_synthesis_receipt"]
                joint["changed_safe_coordinate_count"] += 1
                joint.pop("receipt_payload_sha256")
                joint["receipt_payload_sha256"] = payload_sha256(joint)
            elif kind == "parent":
                parent = changed["private_parent_result"]
                parent["changed_safe_coordinate_count"] += 1
                parent.pop("result_payload_sha256")
                parent["result_payload_sha256"] = payload_sha256(parent)
            elif kind == "prediction":
                changed["prediction"] += "x"
            else:
                joint = changed["joint_synthesis_receipt"]
                joint["positive_signed_credit_count"] = 1
                joint.pop("receipt_payload_sha256")
                joint["receipt_payload_sha256"] = payload_sha256(joint)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25383_joint_synthesis_changed_safe_runtime.py"
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
