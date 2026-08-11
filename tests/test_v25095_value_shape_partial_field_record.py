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

from deepwide_agent import v25095_value_shape_partial_field_record as target  # noqa: E402
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


def field(column: str, source: str, value: str) -> dict[str, str]:
    return {"column": column, "source_field": source, "value": value}


def proposal(fields: list[dict[str, str]], *, ordinal: int = 1) -> str:
    return json.dumps({"records": [{"page_ordinal": ordinal, "fields": fields}]})


def run(fields: list[dict[str, str]], *, pages=(DOCS, PYPI), ordinal: int = 1):
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
    result = target.build_representation(
        prepared,
        proposal(fields, ordinal=ordinal),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )
    return prepared, result, target.validate_receipt(result["content_free_receipt"])


class ValueShapePartialFieldRecordTests(unittest.TestCase):
    def test_authority_selected_page_is_rebased_to_local_one(self) -> None:
        prepared, result, receipt = run(
            [field("Latest version", "Version", "2.4.0")]
        )
        self.assertEqual(prepared["joint_identity_bound_page_count"], 2)
        self.assertTrue(prepared["authority_tiebreak_selected"])
        self.assertEqual(prepared["pages"][0]["page_ordinal"], 1)
        self.assertIn("LOCAL AUTHORITY-SELECTED PAGE", prepared["user"])
        self.assertEqual(receipt["field_lexical_accepted_count"], 1)
        self.assertEqual(receipt["field_page_reference_rejection_count"], 0)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertIn("selected_page=P0001", result["candidate_evidence"])

    def test_unique_date_and_python_shapes_corroborate_unbound_labels(self) -> None:
        _prepared, result, receipt = run(
            [
                field("Latest release date (YYYY-MM-DD)", "Uploaded", "Aug 1, 2026"),
                field("Requires-Python", "Compatibility", ">=3.10"),
            ]
        )
        self.assertEqual(receipt["field_value_shape_accepted_count"], 2)
        self.assertEqual(receipt["field_accepted_count"], 2)
        self.assertEqual(receipt["rendered_field_count"], 2)
        self.assertIn('"binding_mode":"value_shape"', result["candidate_evidence"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))

    def test_exact_target_column_is_mandatory(self) -> None:
        _prepared, result, receipt = run(
            [field("Published", "Uploaded", "Aug 1, 2026")]
        )
        self.assertEqual(receipt["field_target_column_rejection_count"], 1)
        self.assertEqual(receipt["field_accepted_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_source_label_bound_to_other_target_cannot_use_shape(self) -> None:
        _prepared, result, receipt = run(
            [field("Latest release date (YYYY-MM-DD)", "Latest version", "Aug 1, 2026")]
        )
        self.assertEqual(receipt["field_source_label_conflict_rejection_count"], 1)
        self.assertEqual(receipt["field_value_shape_accepted_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_nonunique_target_shape_fails_closed(self) -> None:
        columns = (
            "Package",
            "Release date",
            "Upload date",
        )
        page = {
            **PYPI,
            "content": PYPI["content"] + "\nObserved Aug 1, 2026",
        }
        prepared = target.prepare_record_proposal(QUESTION, columns, (page,))
        result = target.build_representation(
            prepared,
            proposal([field("Release date", "Observed", "Aug 1, 2026")]),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_value_shape_rejection_count"], 1)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_coordinate_ambiguity_rejects_only_that_field(self) -> None:
        duplicate = {
            **PYPI,
            "content": PYPI["content"] + "\nUploaded Aug 1, 2026",
        }
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, (duplicate,))
        result = target.build_representation(
            prepared,
            proposal(
                [
                    field("Latest release date (YYYY-MM-DD)", "Uploaded", "Aug 1, 2026"),
                    field("Latest version", "Version", "2.4.0"),
                ]
            ),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_coordinate_rejection_count"], 1)
        self.assertEqual(receipt["field_lexical_accepted_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 1)

    def test_conflicting_same_target_values_reject_entire_record(self) -> None:
        page = {**PYPI, "content": PYPI["content"] + "\nVersion 2.3.0"}
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, (page,))
        result = target.build_representation(
            prepared,
            proposal(
                [
                    field("Latest version", "Version", "2.4.0"),
                    field("Latest version", "Version", "2.3.0"),
                ]
            ),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["record_conflict_count"], 1)
        self.assertEqual(receipt["field_conflict_rejection_count"], 2)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_wrong_local_page_reference_fails_closed(self) -> None:
        _prepared, result, receipt = run(
            [field("Latest version", "Version", "2.4.0")], ordinal=2
        )
        self.assertEqual(receipt["field_page_reference_rejection_count"], 1)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_resealed_disposition_credit_or_launch_tamper_fails(self) -> None:
        _prepared, _result, receipt = run(
            [field("Latest release date (YYYY-MM-DD)", "Uploaded", "Aug 1, 2026")]
        )
        for kind in ("disposition", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "disposition":
                changed["field_value_shape_rejection_count"] += 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25095_value_shape_partial_field_record.py"
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
