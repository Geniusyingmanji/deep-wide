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

from deepwide_agent import v25075_anchor_bounded_record_region as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Return one table for package Alpha. Columns exactly: Package | Latest version | "
    "Latest release date (YYYY-MM-DD) | Requires-Python."
)
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
ANCHOR = "Canonical record for Package: Alpha"
LEFT = "L" * 400
MIDDLE = "M" * 400
RIGHT = "R" * 400
CONTENT = (
    f"Latest version: 2.4.0 {LEFT} {ANCHOR} {MIDDLE} "
    f"Latest release date: 2026-08-01 {RIGHT} Requires-Python: >=3.10"
)
PAGES = [{"title": "Alpha", "url": "https://example.test/alpha", "content": CONTENT}]
CONTROL = "C" * 8_000


def proposal(*, identity: str = "Alpha", page_ordinal: int = 1) -> dict:
    return {
        "records": [
            {
                "page_ordinal": page_ordinal,
                "record_anchor": ANCHOR,
                "row_identity": identity,
                "fields": [
                    {
                        "column": "Latest version",
                        "source_field": "Latest version",
                        "value": "2.4.0",
                    },
                    {
                        "column": "Latest release date (YYYY-MM-DD)",
                        "source_field": "Latest release date",
                        "value": "2026-08-01",
                    },
                    {
                        "column": "Requires-Python",
                        "source_field": "Requires-Python",
                        "value": ">=3.10",
                    },
                ],
            }
        ]
    }


def run(value: object, *, pages=PAGES) -> dict:
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
    return target.build_representation(
        prepared,
        json.dumps(value),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )


class AnchorBoundedRecordRegionTests(unittest.TestCase):
    def test_fields_need_not_repeat_anchor_and_render(self) -> None:
        value = proposal()
        self.assertTrue(all("quote" not in field for field in value["records"][0]["fields"]))
        result = run(value)
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertEqual(receipt["verified_region_record_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 3)
        self.assertEqual(receipt["rendered_record_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))
        self.assertIn("ANCHOR_BOUNDED_VERIFIED_RECORD", result["candidate_evidence"])

    def test_region_is_bounded_and_can_cover_both_sides_of_anchor(self) -> None:
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, PAGES)
        page = prepared["pages"][0]["content"]
        region = target._bounded_region(page, ANCHOR)
        self.assertIsNotNone(region)
        self.assertLessEqual(len(region[0]), target.MAXIMUM_RECORD_REGION_CHARACTERS)
        result = run(proposal())
        self.assertEqual(result["content_free_receipt"]["verified_field_count"], 3)

    def test_wrong_page_nonunique_anchor_and_wrong_identity_fail_closed(self) -> None:
        wrong_page = run(proposal(page_ordinal=2))
        self.assertEqual(wrong_page["content_free_receipt"]["rejected_page_reference_count"], 1)
        duplicate = run(proposal(), pages=[{"url": "https://example.test/x", "content": CONTENT + " " + ANCHOR}])
        self.assertEqual(
            duplicate["content_free_receipt"]["rejected_nonunique_or_nonverbatim_anchor_count"], 1
        )
        wrong_identity = run(proposal(identity="Beta"))
        self.assertEqual(
            wrong_identity["content_free_receipt"]["rejected_row_identity_binding_count"], 1
        )

    def test_repeated_field_or_value_uses_unique_nearest_pair(self) -> None:
        repeated = "Latest version: 2.4.0 " + CONTENT
        repeated_label = run(
            proposal(),
            pages=[{"url": "https://example.test/x", "content": repeated}],
        )
        self.assertEqual(repeated_label["content_free_receipt"]["verified_region_record_count"], 1)
        repeated_date = CONTENT.replace(
            "Latest release date: 2026-08-01",
            "Latest release date: 2026-08-01 Latest release date: 2026-08-01",
        )
        repeated_value = run(proposal(), pages=[{"url": "https://example.test/x", "content": repeated_date}])
        self.assertEqual(repeated_value["content_free_receipt"]["verified_region_record_count"], 1)

    def test_tied_minimum_label_value_pairs_fail_closed(self) -> None:
        content = CONTENT.replace(
            "Latest release date: 2026-08-01",
            "Latest release date: 2026-08-01 / Latest release date: 2026-08-01",
        )
        value = proposal()
        value["records"][0]["fields"] = [
            {
                "column": "Latest release date (YYYY-MM-DD)",
                "source_field": "Latest release date",
                "value": "2026-08-01",
            }
        ]
        result = run(value, pages=[{"url": "https://example.test/x", "content": content}])
        self.assertEqual(
            result["content_free_receipt"]["rejected_nonunique_field_coordinate_count"], 1
        )

    def test_field_span_over_cap_fails_closed(self) -> None:
        content = f"{ANCHOR} Latest version: {'X' * 1300} 2.4.0"
        result = run(proposal(), pages=[{"url": "https://example.test/x", "content": content}])
        self.assertEqual(result["content_free_receipt"]["rejected_field_span_count"], 1)

    def test_ambiguous_label_and_unknown_value_fail_closed(self) -> None:
        value = proposal()
        value["records"][0]["fields"][0]["source_field"] = "Version date"
        ambiguous = run(value)
        self.assertEqual(
            ambiguous["content_free_receipt"]["rejected_field_label_or_value_binding_count"], 1
        )
        value = proposal()
        value["records"][0]["fields"][0]["value"] = "Unknown"
        unknown = run(value)
        self.assertEqual(
            unknown["content_free_receipt"]["rejected_field_label_or_value_binding_count"], 1
        )

    def test_same_anchor_target_conflict_rejects_entire_record(self) -> None:
        value = proposal()
        other = copy.deepcopy(value["records"][0])
        other["fields"] = [
            {"column": "Latest version", "source_field": "Latest version", "value": "2.3.0"}
        ]
        value["records"].append(other)
        content = CONTENT.replace("Latest version: 2.4.0", "Latest version: 2.4.0 2.3.0")
        result = run(value, pages=[{"url": "https://example.test/x", "content": content}])
        self.assertEqual(result["content_free_receipt"]["ambiguous_same_anchor_record_count"], 1)
        self.assertEqual(result["content_free_receipt"]["rendered_record_count"], 0)

    def test_overlapping_distinct_record_regions_fail_closed(self) -> None:
        second_anchor = "Archived record for Package: Beta"
        content = CONTENT + " Z " * 20 + second_anchor + " Python requirement: >=2.7"
        value = proposal()
        value["records"][0]["fields"] = [value["records"][0]["fields"][0]]
        value["records"].append(
            {
                "page_ordinal": 1,
                "record_anchor": second_anchor,
                "row_identity": "Beta",
                "fields": [
                    {"column": "Requires-Python", "source_field": "Requires-Python", "value": ">=3.10"}
                ],
            }
        )
        original_cap = target.MAXIMUM_RECORD_REGION_CHARACTERS
        target.MAXIMUM_RECORD_REGION_CHARACTERS = 1_200
        try:
            result = run(value, pages=[{"url": "https://example.test/x", "content": content}])
        finally:
            target.MAXIMUM_RECORD_REGION_CHARACTERS = original_cap
        self.assertEqual(result["content_free_receipt"]["overlapping_record_region_count"], 2)
        self.assertEqual(result["content_free_receipt"]["rendered_record_count"], 0)

    def test_empty_invalid_and_transport_failure_preserve_control(self) -> None:
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, PAGES)
        for raw, attempted in ((json.dumps({"records": []}), True), ("bad", True), ("", False)):
            result = target.build_representation(
                prepared,
                raw,
                control_evidence=CONTROL,
                model_call_attempted=attempted,
            )
            with self.subTest(raw=raw, attempted=attempted):
                self.assertEqual(result["candidate_evidence"], CONTROL)
                self.assertFalse(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_resealed_credit_length_or_launch_tamper_fails(self) -> None:
        receipt = run(proposal())["content_free_receipt"]
        for kind in ("credit", "length", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "length":
                changed["candidate_evidence_characters"] += 1
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25075_anchor_bounded_record_region.py"
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
