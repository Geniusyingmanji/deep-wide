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

from deepwide_agent import v25360_quote_coordinate_partial_field_record as target  # noqa: E402


QUESTION = (
    "Use public sources and return a table. Columns exactly: Entity | Release date | License | Status."
)
COLUMNS = ("Entity", "Release date", "License", "Status")
QUOTE = "Alpha release 1. Release date: 2026-01-02. License: MIT. State: Final."
PAGES = [{"title": "Alpha", "url": "https://example.org/alpha", "content": QUOTE}]
CONTROL = "raw evidence " * 1000


def field(column: str, source: str, value: str) -> dict[str, str]:
    return {"column": column, "source_field": source, "value": value}


def record(fields, *, quote=QUOTE, identity="Alpha release 1", page=1):
    return {
        "page_ordinal": page,
        "quote": quote,
        "row_identity": identity,
        "fields": fields,
    }


def run(records, *, pages=PAGES):
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
    return target.build_representation(
        prepared,
        json.dumps({"records": records}),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )


class V25360QuoteCoordinatePartialFieldTests(unittest.TestCase):
    def test_good_fields_survive_one_bad_field_at_same_verified_coordinate(self) -> None:
        result = run(
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
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertEqual(receipt["parsed_field_count"], 3)
        self.assertEqual(receipt["field_accepted_count"], 2)
        self.assertEqual(
            receipt["field_label_or_value_binding_rejection_count"], 1
        )
        self.assertEqual(receipt["verified_partial_record_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 2)
        self.assertTrue(receipt["candidate_evidence_changed"])

    def test_bad_page_quote_or_row_rejects_all_fields(self) -> None:
        cases = (
            record([field("License", "License", "MIT")], page=2),
            record(
                [field("License", "License", "MIT")],
                quote="Alpha release one. License: MIT.",
            ),
            record([field("License", "License", "MIT")], identity="Beta"),
        )
        for item in cases:
            result = run([item])
            with self.subTest(item=item):
                self.assertFalse(
                    result["content_free_receipt"]["candidate_evidence_changed"]
                )

    def test_unknown_missing_source_or_missing_value_is_omitted(self) -> None:
        result = run(
            [
                record(
                    [
                        field("License", "License", "Unknown"),
                        field("License", "Terms", "MIT"),
                        field("License", "License", "GPL"),
                    ]
                )
            ]
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_unknown_rejection_count"], 1)
        self.assertEqual(
            receipt["field_label_or_value_binding_rejection_count"], 2
        )
        self.assertEqual(receipt["record_zero_accepted_field_count"], 1)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_same_coordinate_same_column_conflict_rejects_record(self) -> None:
        result = run(
            [
                record([field("License", "License", "MIT")]),
                record([field("License", "License", "Final")]),
            ]
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["record_conflict_count"], 1)
        self.assertEqual(receipt["field_conflict_rejection_count"], 2)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_exact_duplicate_collapses_without_extra_credit(self) -> None:
        item = record([field("License", "License", "MIT")])
        result = run([item, copy.deepcopy(item)])
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["field_accepted_count"], 1)
        self.assertEqual(receipt["field_exact_duplicate_rejection_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])

    def test_ambiguous_source_label_is_omitted(self) -> None:
        columns = ("Entity", "Release", "Release date")
        prepared = target.prepare_record_proposal(QUESTION, columns, PAGES)
        result = target.build_representation(
            prepared,
            json.dumps(
                {
                    "records": [
                        record([field("Release", "Release", "2026-01-02")])
                    ]
                }
            ),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(
            receipt["field_label_or_value_binding_rejection_count"], 1
        )
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_resealed_count_or_credit_tamper_fails(self) -> None:
        result = run([record([field("License", "License", "MIT")])])
        for kind in ("count", "credit"):
            changed = copy.deepcopy(result["content_free_receipt"])
            if kind == "count":
                changed["field_accepted_count"] += 1
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_label_blind_and_has_no_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25360_quote_coordinate_partial_field_record.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
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
        for forbidden in (
            "ground_truth",
            "answer_key",
            "official_eval",
            "api_key",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
