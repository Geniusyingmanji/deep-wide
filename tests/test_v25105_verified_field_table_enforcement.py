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

from deepwide_agent import v25100_complete_column_value_shape_record as binding  # noqa: E402
from deepwide_agent import v25105_verified_field_table_enforcement as target  # noqa: E402
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
PAGE = {
    "title": "Alpha-Kit · PyPI",
    "url": "https://pypi.org/project/Alpha-Kit/",
    "content": "Alpha-Kit\nVersion 2.4.0\nUploaded Aug 1, 2026\nCompatibility >=3.10",
}
PREDICTION = (
    "```markdown\n"
    "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
    "| --- | --- | --- | --- |\n"
    "| Alpha-Kit | 2.3.0 | Unknown | >=3.9 |\n"
    "```"
)


def proposal(*, duplicate_identity: bool = False) -> str:
    return json.dumps(
        {
            "records": [
                {
                    "page_ordinal": 1,
                    "columns": [
                        {
                            "column": "Latest version",
                            "status": "found",
                            "source_field": "Version",
                            "value": "2.4.0",
                        },
                        {
                            "column": "Latest release date (YYYY-MM-DD)",
                            "status": "found",
                            "source_field": "Uploaded",
                            "value": "Aug 1, 2026",
                        },
                        {"column": "Requires-Python", "status": "unavailable"},
                    ],
                }
            ]
        }
    )


class VerifiedFieldTableEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prepared = binding.prepare_record_proposal(QUESTION, COLUMNS, (PAGE,))

    def test_verified_fields_override_only_exact_target_cells(self) -> None:
        result = target.enforce_verified_fields(
            PREDICTION,
            COLUMNS,
            self.prepared,
            proposal(),
            model_call_attempted=True,
        )
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertEqual(receipt["verified_field_count"], 2)
        self.assertEqual(receipt["applied_field_count"], 2)
        self.assertEqual(receipt["changed_cell_count"], 2)
        self.assertEqual(receipt["normalized_date_count"], 1)
        self.assertTrue(receipt["unique_identity_row_matched"])
        self.assertTrue(receipt["output_changed"])
        self.assertIn("| Alpha-Kit | 2.4.0 | 2026-08-01 | >=3.9 |", result["prediction"])

    def test_already_matching_verified_fields_are_counted_without_change(self) -> None:
        matching = PREDICTION.replace("2.3.0", "2.4.0").replace("Unknown", "2026-08-01")
        result = target.enforce_verified_fields(
            matching,
            COLUMNS,
            self.prepared,
            proposal(),
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["applied_field_count"], 2)
        self.assertEqual(receipt["changed_cell_count"], 0)
        self.assertFalse(receipt["output_changed"])
        self.assertEqual(result["prediction"], matching)

    def test_ambiguous_identity_row_fails_closed(self) -> None:
        ambiguous = PREDICTION.replace(
            "\n```",
            "\n| Alpha Kit | 9.9.9 | 2020-01-01 | >=3.8 |\n```",
        )
        result = target.enforce_verified_fields(
            ambiguous,
            COLUMNS,
            self.prepared,
            proposal(),
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["unique_identity_row_matched"])
        self.assertEqual(receipt["applied_field_count"], 0)
        self.assertEqual(result["prediction"], ambiguous)

    def test_invalid_proposal_or_table_fails_closed(self) -> None:
        for candidate, output in (
            (PREDICTION, "not-json"),
            ("not-a-table", proposal()),
        ):
            with self.subTest(candidate=candidate):
                result = target.enforce_verified_fields(
                    candidate,
                    COLUMNS,
                    self.prepared,
                    output,
                    model_call_attempted=True,
                )
                self.assertEqual(result["prediction"], candidate)
                self.assertEqual(result["content_free_receipt"]["applied_field_count"], 0)

    def test_resealed_count_credit_or_launch_tamper_fails(self) -> None:
        receipt = target.enforce_verified_fields(
            PREDICTION,
            COLUMNS,
            self.prepared,
            proposal(),
            model_call_attempted=True,
        )["content_free_receipt"]
        for kind in ("count", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "count":
                changed["changed_cell_count"] += 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25105_verified_field_table_enforcement.py"
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
