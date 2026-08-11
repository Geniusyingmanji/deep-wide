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

from deepwide_agent import v25080_visible_identity_page_record as target  # noqa: E402
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
        "Project description",
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


def proposal(*, page_ordinal: int = 1) -> dict:
    return {
        "records": [
            {
                "page_ordinal": page_ordinal,
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


def run(value: object, *, question=QUESTION, pages=(PAGE,)) -> dict:
    prepared = target.prepare_record_proposal(question, COLUMNS, pages)
    return target.build_representation(
        prepared,
        json.dumps(value),
        control_evidence=CONTROL,
        model_call_attempted=True,
    )


class VisibleIdentityPageRecordTests(unittest.TestCase):
    def test_singular_visible_identity_binds_url_and_title_then_renders(self) -> None:
        result = run(proposal())
        receipt = target.validate_receipt(result["content_free_receipt"])
        self.assertTrue(receipt["visible_identity_present"])
        self.assertEqual(receipt["identity_url_match_page_count"], 1)
        self.assertEqual(receipt["identity_surface_match_page_count"], 1)
        self.assertEqual(receipt["joint_identity_bound_page_count"], 1)
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 3)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))
        self.assertIn("VISIBLE_IDENTITY_PAGE_RECORD", result["candidate_evidence"])

    def test_visible_identity_parser_is_strict_and_label_blind(self) -> None:
        self.assertEqual(target.visible_identity(QUESTION), "Alpha-Kit")
        for question in (
            QUESTION.replace("<PACKAGE>", "<package>").replace("</PACKAGE>", "</package>"),
            QUESTION + " Also <ENTITY>Beta</ENTITY>.",
            QUESTION.replace("PACKAGE", "PACKAGES"),
            QUESTION.replace("Alpha-Kit", "Unknown"),
            "Return a row for Alpha-Kit without a visible tag.",
        ):
            with self.subTest(question=question):
                self.assertIsNone(target.visible_identity(question))

    def test_body_only_or_substring_title_is_insufficient(self) -> None:
        cases = (
            {**PAGE, "title": "Unrelated", "content": "Alpha-Kit\n" + CONTENT},
            {**PAGE, "title": "Alpha-Kit documentation archive"},
            {**PAGE, "url": "https://pypi.org/project/Alpha-Kit-extra/"},
        )
        for page in cases:
            result = run(proposal(), pages=(page,))
            with self.subTest(page=page):
                self.assertFalse(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_ambiguous_two_identity_pages_fail_closed(self) -> None:
        other = {
            **PAGE,
            "url": "https://docs.example.test/Alpha-Kit/index.html",
            "title": "Alpha Kit | Documentation",
        }
        result = run(proposal(), pages=(PAGE, other))
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["joint_identity_bound_page_count"], 2)
        self.assertEqual(receipt["bounded_page_count"], 0)
        self.assertEqual(receipt["rejected_nonunique_identity_page_count"], 1)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_wrong_page_reference_label_unknown_or_tied_quote_fail_closed(self) -> None:
        wrong_page = run(proposal(page_ordinal=2))
        self.assertEqual(wrong_page["content_free_receipt"]["rejected_page_reference_count"], 1)

        value = proposal()
        value["records"][0]["fields"][0]["source_field"] = "Version date"
        bad_label = run(value)
        self.assertEqual(
            bad_label["content_free_receipt"]["rejected_field_label_or_value_binding_count"], 1
        )

        value = proposal()
        value["records"][0]["fields"][0]["value"] = "Unknown"
        unknown = run(value)
        self.assertEqual(
            unknown["content_free_receipt"]["rejected_field_label_or_value_binding_count"], 1
        )

        tied = CONTENT.replace(
            "Latest version: 2.4.0",
            "Latest version: 2.4.0 / Latest version: 2.4.0",
        )
        tied_result = run(proposal(), pages=({**PAGE, "content": tied},))
        self.assertEqual(
            tied_result["content_free_receipt"]["rejected_nonunique_field_coordinate_count"], 1
        )

    def test_empty_invalid_or_unattempted_proposal_preserves_control(self) -> None:
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
                self.assertFalse(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_resealed_credit_length_or_launch_tamper_fails(self) -> None:
        receipt = run(proposal())["content_free_receipt"]
        for kind in ("credit", "length", "launch", "joint"):
            changed = copy.deepcopy(receipt)
            if kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "length":
                changed["candidate_evidence_characters"] += 1
            elif kind == "launch":
                changed["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["joint_identity_bound_page_count"] = 2
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_has_no_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25080_visible_identity_page_record.py"
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
