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

from deepwide_agent import v25085_identity_bound_partial_field_record as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Return one table for <PACKAGE>Alpha-Kit</PACKAGE>. "
    "Columns exactly: Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python."
)
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
CONTENT = "\n".join(
    (
        "Alpha Kit",
        "Latest version: 2.4.0",
        "Latest release date: 2026-08-01",
        "Requires-Python: >=3.10",
    )
)
PAGE = {
    "title": "Alpha-Kit · PyPI",
    "url": "https://pypi.org/project/Alpha-Kit/",
    "content": CONTENT,
}
CONTROL = "C" * 8_000


def field(column: str, source: str, value: str) -> dict[str, str]:
    return {"column": column, "source_field": source, "value": value}


def proposal(fields: list[dict[str, str]]) -> dict:
    return {"records": [{"page_ordinal": 1, "fields": fields}]}


def run(value: object, *, pages=(PAGE,)) -> dict:
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
    return target.build_representation(
        prepared,
        json.dumps(value),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )


class IdentityBoundPartialFieldTests(unittest.TestCase):
    def test_good_field_survives_bad_and_unknown_fields(self) -> None:
        value = proposal(
            [
                field("Latest version", "Latest version", "2.4.0"),
                field("Latest release date (YYYY-MM-DD)", "Published at", "2026-08-01"),
                field("Requires-Python", "Requires-Python", "Unknown"),
            ]
        )
        result = run(value)
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertEqual(receipt["parsed_field_count"], 3)
        self.assertEqual(receipt["field_accepted_count"], 1)
        self.assertEqual(receipt["field_label_or_value_binding_rejection_count"], 1)
        self.assertEqual(receipt["field_unknown_rejection_count"], 1)
        self.assertEqual(receipt["verified_partial_record_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertIn("IDENTITY_BOUND_PARTIAL_RECORD", result["candidate_evidence"])
        self.assertIn('"value":"2.4.0"', result["candidate_evidence"])
        self.assertNotIn("Unknown", result["candidate_evidence"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))

    def test_all_bad_fields_preserve_control_with_complete_dispositions(self) -> None:
        result = run(
            proposal(
                [
                    field("Latest version", "Version date", "2.4.0"),
                    field("Requires-Python", "Requires-Python", "Unknown"),
                ]
            )
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["parsed_field_count"], 2)
        self.assertEqual(receipt["field_label_or_value_binding_rejection_count"], 1)
        self.assertEqual(receipt["field_unknown_rejection_count"], 1)
        self.assertEqual(receipt["verified_partial_record_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_exact_duplicate_is_collapsed_and_counted(self) -> None:
        item = field("Latest version", "Latest version", "2.4.0")
        result = run(proposal([item, copy.deepcopy(item)]))
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_accepted_count"], 1)
        self.assertEqual(receipt["field_exact_duplicate_rejection_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 1)

    def test_conflicting_values_reject_entire_record(self) -> None:
        page = {**PAGE, "content": CONTENT.replace("2.4.0", "2.4.0 2.3.0")}
        result = run(
            proposal(
                [
                    field("Latest version", "Latest version", "2.4.0"),
                    field("Latest version", "Latest version", "2.3.0"),
                    field("Requires-Python", "Requires-Python", ">=3.10"),
                ]
            ),
            pages=(page,),
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["record_conflict_count"], 1)
        self.assertEqual(receipt["field_conflict_rejection_count"], 2)
        self.assertEqual(receipt["field_accepted_count"], 1)
        self.assertEqual(receipt["verified_partial_record_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_coordinate_ambiguity_rejects_only_that_field(self) -> None:
        page = {
            **PAGE,
            "content": CONTENT.replace(
                "Latest version: 2.4.0",
                "Latest version: 2.4.0 / Latest version: 2.4.0",
            ),
        }
        result = run(
            proposal(
                [
                    field("Latest version", "Latest version", "2.4.0"),
                    field("Requires-Python", "Requires-Python", ">=3.10"),
                ]
            ),
            pages=(page,),
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_coordinate_rejection_count"], 1)
        self.assertEqual(receipt["field_accepted_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 1)

    def test_nonunique_identity_page_disposes_every_field(self) -> None:
        other = {**PAGE, "url": "https://docs.example.test/Alpha-Kit/index.html"}
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, (PAGE, other))
        value = proposal([field("Latest version", "Latest version", "2.4.0")])
        result = target.build_representation(
            prepared,
            json.dumps(value),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_identity_page_rejection_count"], 1)
        self.assertEqual(receipt["rejected_nonunique_identity_page_record_count"], 1)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_empty_invalid_and_unattempted_preserve_control(self) -> None:
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, (PAGE,))
        for raw, attempted in ((json.dumps({"records": []}), True), ("bad", True), ("", False)):
            result = target.build_representation(
                prepared,
                raw,
                control_evidence=CONTROL,
                model_call_attempted=attempted,
            )
            with self.subTest(raw=raw, attempted=attempted):
                self.assertEqual(result["candidate_evidence"], CONTROL)
                self.assertEqual(result["content_free_receipt"]["parsed_field_count"], 0)

    def test_resealed_disposition_credit_or_launch_tamper_fails(self) -> None:
        receipt = run(proposal([field("Latest version", "Latest version", "2.4.0")]))[
            "content_free_receipt"
        ]
        for kind in ("disposition", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "disposition":
                changed["field_unknown_rejection_count"] += 1
            elif kind == "credit":
                changed["rejected_or_unknown_field_assigns_positive_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25085_identity_bound_partial_field_record.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
