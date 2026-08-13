from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25346_grounded_fact_bootstrap as parent  # noqa: E402
from deepwide_agent import v25361_partial_field_grounded_fact_bootstrap as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use public sources and return a table. Columns exactly: "
    "Entity | Release date | License | Status."
)
COLUMNS = ["Entity", "Release date", "License", "Status"]
QUOTE = (
    "Alpha release 1. Release date: 2026-01-02. "
    "License: MIT. State: Final."
)
PAGES = [
    {
        "url": "https://example.org/alpha",
        "title": "Alpha release",
        "content": QUOTE + " Additional public release material follows.",
    }
]
PLAN = {
    "pivots": ["Alpha release 1"],
    "row_targets": ["Alpha release 1"],
    "authority_terms": ["public release"],
    "queries": ["Alpha release 1", "Alpha release 1 public release"],
}


def field(column: str, source: str, value: str) -> dict[str, str]:
    return {"column": column, "source_field": source, "value": value}


def record(fields, *, quote=QUOTE, identity="Alpha release 1"):
    return {
        "page_ordinal": 1,
        "quote": quote,
        "row_identity": identity,
        "fields": fields,
    }


def joint(records) -> str:
    return json.dumps({**PLAN, "records": records}, ensure_ascii=False)


def production_user() -> str:
    evidence = (
        "[[EVIDENCE 1]]\n"
        "title=Alpha release\n"
        "url=https://example.org/alpha\n"
        "content="
        + PAGES[0]["content"]
        + "\n\n"
        + ("background release material " * 180)
    )
    return (
        "VISIBLE QUESTION:\n"
        + QUESTION
        + "\n\nREQUIRED COLUMNS:\n"
        + json.dumps(COLUMNS)
        + "\n\nBOUNDED WEB MATERIAL:\n"
        + evidence
        + "\n\nProduce the best-supported answer possible within the supplied material."
    )


def build(records):
    return target.build_bootstrap(
        question=QUESTION,
        columns=COLUMNS,
        first_wave_pages=PAGES,
        grounded_model_output=joint(records),
        production_user=production_user(),
        model_call_attempted=True,
    )


class V25361PartialFieldGroundedFactBootstrapTests(unittest.TestCase):
    def test_joint_prompt_and_parent_plan_projection_are_parent_byte_exact(self) -> None:
        parent_system = "GROUNDING" + parent.JOINT_SYSTEM_SUFFIX[:0]
        with self.assertRaises(ValueError):
            target.joint_system(parent_system)
        from deepwide_agent import v25117_grounded_target_record_plan as grounded

        actual_system = grounded.SYSTEM_PROMPT + "\n\nPARENT CHECKLIST"
        self.assertEqual(
            target.joint_system(actual_system), parent.joint_system(actual_system)
        )
        raw = joint([record([field("License", "License", "MIT")])])
        self.assertEqual(
            target.parent_grounded_output(raw), parent.parent_grounded_output(raw)
        )

    def test_good_fields_survive_bad_field_and_prompt_length_is_preserved(self) -> None:
        control = production_user()
        value = build(
            [
                record(
                    [
                        field("Release date", "Release date", "2026-01-02"),
                        field("License", "License", "MIT"),
                        field("Status", "Unsupported label", "Final"),
                    ]
                )
            ]
        )
        receipt = target.validate_receipt(value["content_free_receipt"])
        self.assertEqual(len(value["candidate_production_user"]), len(control))
        self.assertNotEqual(value["candidate_production_user"], control)
        self.assertEqual(receipt["parsed_field_count"], 3)
        self.assertEqual(receipt["field_accepted_count"], 2)
        self.assertEqual(
            receipt["field_label_or_value_binding_rejection_count"], 1
        )
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 2)
        self.assertEqual(receipt["additional_model_call_count"], 0)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertTrue(receipt["candidate_production_prompt_changed"])

    def test_all_valid_fields_are_byte_equivalent_to_parent_bootstrap(self) -> None:
        records = [
            record(
                [
                    field("Release date", "Release date", "2026-01-02"),
                    field("License", "License", "MIT"),
                ]
            )
        ]
        kwargs = {
            "question": QUESTION,
            "columns": COLUMNS,
            "first_wave_pages": PAGES,
            "grounded_model_output": joint(records),
            "production_user": production_user(),
            "model_call_attempted": True,
        }
        old = parent.build_bootstrap(**kwargs)
        new = target.build_bootstrap(**kwargs)
        self.assertEqual(
            new["parent_grounded_output"], old["parent_grounded_output"]
        )
        self.assertEqual(
            new["candidate_production_user"], old["candidate_production_user"]
        )

    def test_bad_quote_row_and_same_coordinate_conflict_remain_noop(self) -> None:
        cases = (
            [
                record(
                    [field("License", "License", "MIT")],
                    quote="Alpha release one has License MIT.",
                )
            ],
            [record([field("License", "License", "MIT")], identity="Beta")],
            [
                record([field("License", "License", "MIT")]),
                record([field("License", "License", "Final")]),
            ],
        )
        for records in cases:
            with self.subTest(records=records):
                value = build(records)
                self.assertEqual(value["candidate_production_user"], production_user())
                self.assertFalse(
                    value["content_free_receipt"][
                        "candidate_production_prompt_changed"
                    ]
                )

    def test_parent_only_invalid_or_one_column_output_is_total_noop(self) -> None:
        control = production_user()
        cases = (
            (json.dumps(PLAN), COLUMNS),
            ("not-json", COLUMNS),
            (joint([record([field("License", "License", "MIT")])]), ["Result"]),
        )
        for raw, columns in cases:
            with self.subTest(raw=raw[:8], columns=columns):
                value = target.build_bootstrap(
                    question=QUESTION,
                    columns=columns,
                    first_wave_pages=PAGES,
                    grounded_model_output=raw,
                    production_user=control,
                    model_call_attempted=True,
                )
                self.assertEqual(value["candidate_production_user"], control)
                self.assertEqual(value["additional_model_call_count"], 0)

    def test_resealed_count_credit_or_authorization_tamper_fails(self) -> None:
        value = build([record([field("License", "License", "MIT")])])
        for kind in ("count", "credit", "authorization"):
            changed = copy.deepcopy(value)
            receipt = changed["content_free_receipt"]
            if kind == "count":
                receipt["field_accepted_count"] += 1
            elif kind == "credit":
                receipt["positive_signed_credit_count"] = 1
            else:
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_bootstrap(changed)

    def test_component_is_pure_label_blind_and_build_only(self) -> None:
        relative = Path(
            "src/deepwide_agent/v25361_partial_field_grounded_fact_bootstrap.py"
        )
        source = (ROOT / relative).read_text(encoding="utf-8")
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
        for forbidden_call in (
            "open(",
            "getenv(",
            "run_official_eval_local(",
        ):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
