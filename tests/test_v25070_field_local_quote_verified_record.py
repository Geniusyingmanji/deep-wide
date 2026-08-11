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

from deepwide_agent import v25070_field_local_quote_verified_record as target  # noqa: E402
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
LEFT_FILL = "L" * 620
RIGHT_FILL = "R" * 620
CONTENT = (
    f"Project details. Latest version: 2.4.0 {LEFT_FILL} {ANCHOR} "
    f"Latest release date: 2026-08-01 {RIGHT_FILL} "
    "Requires-Python: >=3.10. End."
)
PAGES = [{"title": "Alpha", "url": "https://example.test/alpha", "content": CONTENT}]
CONTROL = "R" * 8_000


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
                        "quote": f"Latest version: 2.4.0 {LEFT_FILL} {ANCHOR}",
                        "source_field": "Latest version",
                        "value": "2.4.0",
                    },
                    {
                        "column": "Latest release date (YYYY-MM-DD)",
                        "quote": f"{ANCHOR} Latest release date: 2026-08-01",
                        "source_field": "Latest release date",
                        "value": "2026-08-01",
                    },
                    {
                        "column": "Requires-Python",
                        "quote": f"{ANCHOR} Latest release date: 2026-08-01 {RIGHT_FILL} Requires-Python: >=3.10",
                        "source_field": "Requires-Python",
                        "value": ">=3.10",
                    },
                ],
            }
        ]
    }


def run(value: object) -> dict:
    prepared = target.prepare_record_proposal(QUESTION, COLUMNS, PAGES)
    return target.build_representation(
        prepared,
        json.dumps(value),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )


class FieldLocalQuoteVerifiedRecordTests(unittest.TestCase):
    def test_field_local_quotes_share_anchor_and_naturally_render(self) -> None:
        result = run(proposal())
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertEqual(receipt["verified_anchor_record_count"], 1)
        self.assertEqual(receipt["verified_field_quote_count"], 3)
        self.assertEqual(receipt["rendered_record_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))
        self.assertIn("FIELD_LOCAL_QUOTE_VERIFIED_RECORD", result["candidate_evidence"])

    def test_old_single_quote_contract_cannot_represent_split_fields(self) -> None:
        quotes = [field["quote"] for field in proposal()["records"][0]["fields"]]
        self.assertFalse(any(all(value in quote for value in ("2.4.0", "2026-08-01", ">=3.10")) for quote in quotes))
        self.assertGreater(
            len(CONTENT[CONTENT.index("Latest version") : CONTENT.index(">=3.10") + len(">=3.10")]),
            target.MAXIMUM_FIELD_QUOTE_CHARACTERS,
        )
        result = run(proposal())
        self.assertTrue(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_cross_page_field_splice_fails_closed(self) -> None:
        value = proposal()
        value["records"][0]["fields"][0]["quote"] = "Package: Alpha Latest version: 9.9.9"
        result = run(value)
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["verified_anchor_record_count"], 0)
        self.assertEqual(receipt["rejected_field_quote_binding_count"], 1)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_field_quote_without_shared_anchor_fails_closed(self) -> None:
        value = proposal()
        value["records"][0]["fields"][1]["quote"] = "Latest release date: 2026-08-01"
        result = run(value)
        self.assertEqual(result["content_free_receipt"]["rejected_field_quote_binding_count"], 1)
        self.assertFalse(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_nonunique_anchor_fails_closed(self) -> None:
        pages = [{"url": "https://example.test/x", "content": CONTENT + " " + ANCHOR}]
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
        result = target.build_representation(
            prepared,
            json.dumps(proposal()),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        self.assertEqual(
            result["content_free_receipt"]["rejected_nonunique_or_nonverbatim_anchor_count"],
            1,
        )

    def test_wrong_identity_and_ambiguous_label_fail_closed(self) -> None:
        wrong = run(proposal(identity="Beta"))
        self.assertEqual(wrong["content_free_receipt"]["rejected_row_identity_binding_count"], 1)
        value = proposal()
        value["records"][0]["fields"][0]["source_field"] = "Version date"
        ambiguous = run(value)
        self.assertEqual(
            ambiguous["content_free_receipt"]["rejected_field_quote_binding_count"],
            1,
        )

    def test_same_anchor_target_conflict_rejects_entire_record(self) -> None:
        value = proposal()
        other = copy.deepcopy(value["records"][0])
        other["fields"] = [
            {
                "column": "Latest version",
                "quote": f"Latest version: 2.4.0 {LEFT_FILL} {ANCHOR}",
                "source_field": "Latest version",
                "value": "2.4",
            }
        ]
        value["records"].append(other)
        result = run(value)
        self.assertEqual(result["content_free_receipt"]["ambiguous_same_anchor_record_count"], 1)
        self.assertEqual(result["content_free_receipt"]["rendered_record_count"], 0)

    def test_distinct_anchor_coordinates_preserve_same_identity_records(self) -> None:
        content = CONTENT + " Archive record for Package: Alpha Archived version: 1.0.0."
        pages = [{"url": "https://example.test/x", "content": content}]
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
        value = proposal()
        value["records"].append(
            {
                "page_ordinal": 1,
                "record_anchor": "Archive record for Package: Alpha",
                "row_identity": "Alpha",
                "fields": [
                    {
                        "column": "Latest version",
                        "quote": "Archive record for Package: Alpha Archived version: 1.0.0",
                        "source_field": "Archived version",
                        "value": "1.0.0",
                    }
                ],
            }
        )
        result = target.build_representation(
            prepared,
            json.dumps(value),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        self.assertEqual(result["content_free_receipt"]["verified_anchor_record_count"], 2)
        self.assertEqual(result["content_free_receipt"]["rendered_record_count"], 2)

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
        path = ROOT / "src/deepwide_agent/v25070_field_local_quote_verified_record.py"
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
