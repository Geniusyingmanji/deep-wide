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

from deepwide_agent import v25100_complete_column_value_shape_record as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use PyPI as the visible authority for <PACKAGE>Alpha-Kit</PACKAGE>. "
    "Columns exactly: Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python."
)
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
PYPI = {
    "title": "Alpha-Kit · PyPI",
    "url": "https://pypi.org/project/Alpha-Kit/",
    "content": "\n".join(
        (
            "Alpha-Kit",
            "Version 2.4.0",
            "Uploaded Aug 1, 2026",
            "Compatibility >=3.10",
        )
    ),
}
DOCS = {
    "title": "Alpha-Kit | Documentation",
    "url": "https://docs.example.test/Alpha-Kit/",
    "content": "Alpha-Kit\nVersion 2.4.0",
}
CONTROL = "C" * 8_000


def found(column: str, source: str, value: str) -> dict[str, str]:
    return {
        "column": column,
        "status": "found",
        "source_field": source,
        "value": value,
    }


def unavailable(column: str) -> dict[str, str]:
    return {"column": column, "status": "unavailable"}


def proposal(columns: list[dict[str, str]], *, ordinal: int = 1) -> str:
    return json.dumps(
        {"records": [{"page_ordinal": ordinal, "columns": columns}]},
        ensure_ascii=False,
    )


def run(
    output: object,
    *,
    pages=(DOCS, PYPI),
    attempted: bool = True,
):
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
    result = target.build_representation(
        prepared,
        output,
        control_evidence=CONTROL,
        model_call_attempted=attempted,
    )
    return prepared, result, target.validate_receipt(result["content_free_receipt"])


class CompleteColumnValueShapeRecordTests(unittest.TestCase):
    def test_complete_found_and_unavailable_vector_is_verified(self) -> None:
        prepared, result, receipt = run(
            proposal(
                [
                    found("Latest version", "Version", "2.4.0"),
                    found(
                        "Latest release date (YYYY-MM-DD)",
                        "Uploaded",
                        "Aug 1, 2026",
                    ),
                    unavailable("Requires-Python"),
                ]
            )
        )
        self.assertEqual(
            prepared["required_non_key_columns"],
            COLUMNS[1:],
        )
        self.assertEqual(prepared["pages"][0]["page_ordinal"], 1)
        self.assertTrue(receipt["complete_column_proposal_strictly_valid"])
        self.assertEqual(receipt["submitted_column_disposition_count"], 3)
        self.assertEqual(receipt["found_column_disposition_count"], 2)
        self.assertEqual(receipt["unavailable_column_disposition_count"], 1)
        self.assertEqual(receipt["parent_parsed_field_count"], 2)
        self.assertEqual(receipt["parent_accepted_field_count"], 2)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertIn('"binding_mode":"value_shape"', result["candidate_evidence"])

    def test_all_unavailable_is_complete_but_does_not_create_exposure(self) -> None:
        _prepared, result, receipt = run(
            proposal([unavailable(column) for column in COLUMNS[1:]])
        )
        self.assertTrue(receipt["complete_column_proposal_strictly_valid"])
        self.assertEqual(receipt["submitted_column_disposition_count"], 3)
        self.assertEqual(receipt["found_column_disposition_count"], 0)
        self.assertEqual(receipt["parent_parsed_field_count"], 0)
        self.assertFalse(receipt["candidate_evidence_changed"])
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_missing_reordered_duplicate_or_extra_column_fails_closed(self) -> None:
        valid = [
            found("Latest version", "Version", "2.4.0"),
            unavailable("Latest release date (YYYY-MM-DD)"),
            unavailable("Requires-Python"),
        ]
        cases = {
            "missing": valid[:-1],
            "reordered": [valid[1], valid[0], valid[2]],
            "duplicate": [valid[0], valid[0], valid[2]],
            "extra": [*valid, unavailable("Undeclared")],
        }
        for name, columns in cases.items():
            with self.subTest(name=name):
                _prepared, result, receipt = run(proposal(columns))
                self.assertFalse(receipt["complete_column_proposal_strictly_valid"])
                self.assertEqual(receipt["submitted_column_disposition_count"], 0)
                self.assertEqual(receipt["parent_parsed_field_count"], 0)
                self.assertFalse(receipt["candidate_evidence_changed"])
                self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_disposition_shape_and_extra_fields_fail_closed(self) -> None:
        malformed = (
            {"column": "Latest version", "status": "found", "source_field": "Version"},
            {
                "column": "Latest version",
                "status": "unavailable",
                "value": "2.4.0",
            },
            {
                "column": "Latest version",
                "status": "found",
                "source_field": "Version",
                "value": "2.4.0",
                "extra": "x",
            },
        )
        for first in malformed:
            with self.subTest(first=first):
                columns = [
                    first,
                    unavailable("Latest release date (YYYY-MM-DD)"),
                    unavailable("Requires-Python"),
                ]
                _prepared, result, receipt = run(proposal(columns))
                self.assertFalse(receipt["complete_column_proposal_strictly_valid"])
                self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_no_selected_page_accepts_only_empty_records(self) -> None:
        prepared, result, receipt = run(json.dumps({"records": []}), pages=())
        self.assertEqual(prepared["pages"], ())
        self.assertTrue(receipt["complete_column_proposal_strictly_valid"])
        self.assertFalse(receipt["selected_page_available"])
        self.assertEqual(receipt["submitted_column_disposition_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

        _prepared, bad_result, bad_receipt = run(
            proposal([unavailable(column) for column in COLUMNS[1:]]),
            pages=(),
        )
        self.assertFalse(bad_receipt["complete_column_proposal_strictly_valid"])
        self.assertEqual(bad_result["candidate_evidence"], CONTROL)

    def test_found_field_remains_subject_to_parent_coordinate_verifier(self) -> None:
        _prepared, result, receipt = run(
            proposal(
                [
                    found("Latest version", "Version", "9.9.9"),
                    unavailable("Latest release date (YYYY-MM-DD)"),
                    unavailable("Requires-Python"),
                ]
            )
        )
        parent = receipt["parent_value_shape_receipt"]
        self.assertTrue(receipt["complete_column_proposal_strictly_valid"])
        self.assertEqual(receipt["found_column_disposition_count"], 1)
        self.assertEqual(receipt["parent_parsed_field_count"], 1)
        self.assertEqual(receipt["parent_accepted_field_count"], 0)
        self.assertEqual(parent["field_coordinate_rejection_count"], 1)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_not_attempted_cannot_claim_a_complete_vector(self) -> None:
        _prepared, result, receipt = run(
            proposal([unavailable(column) for column in COLUMNS[1:]]),
            attempted=False,
        )
        self.assertFalse(receipt["complete_column_proposal_strictly_valid"])
        self.assertEqual(receipt["submitted_column_disposition_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_resealed_count_parent_credit_or_launch_tamper_fails(self) -> None:
        _prepared, _result, receipt = run(
            proposal(
                [
                    found("Latest version", "Version", "2.4.0"),
                    unavailable("Latest release date (YYYY-MM-DD)"),
                    unavailable("Requires-Python"),
                ]
            )
        )
        for kind in ("count", "parent", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "count":
                changed["found_column_disposition_count"] += 1
            elif kind == "parent":
                changed["parent_accepted_field_count"] += 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25100_complete_column_value_shape_record.py"
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
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
