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

from deepwide_agent import v25090_visible_authority_partial_field_record as target  # noqa: E402
from deepwide_agent.clients import canonicalize_url  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
CONTROL = "C" * 8_000
PYPI = {
    "title": "Alpha-Kit · PyPI",
    "url": "https://pypi.org/project/Alpha-Kit/",
    "content": "Alpha-Kit\nLatest version: 2.4.0\nRequires-Python: >=3.10",
}
DOCS = {
    "title": "Alpha-Kit | Documentation",
    "url": "https://docs.example.test/Alpha-Kit/",
    "content": "Alpha-Kit\nLatest version: 2.4.0\nRequires-Python: >=3.10",
}


def question(authority: str = "PyPI") -> str:
    return (
        "Use public sources and the visible "
        + authority
        + " authority for <PACKAGE>Alpha-Kit</PACKAGE>. Columns exactly: "
        + " | ".join(COLUMNS)
        + "."
    )


def proposal() -> str:
    return json.dumps(
        {
            "records": [
                {
                    "page_ordinal": 1,
                    "fields": [
                        {
                            "column": "Latest version",
                            "source_field": "Latest version",
                            "value": "2.4.0",
                        }
                    ],
                }
            ]
        }
    )


class VisibleAuthorityPartialFieldTests(unittest.TestCase):
    def test_unique_visible_authority_resolves_multiple_strict_identity_pages(self) -> None:
        prepared = target.prepare_record_proposal(question(), COLUMNS, (PYPI, DOCS))
        self.assertEqual(prepared["joint_identity_bound_page_count"], 2)
        self.assertEqual(prepared["bounded_page_count"], 1)
        self.assertEqual(prepared["pages"][0]["url"], canonicalize_url(PYPI["url"]))
        result = target.build_representation(
            prepared,
            proposal(),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        receipt = target.validate_receipt(result["content_free_receipt"])
        selection = receipt["authority_selection_receipt"]
        partial = receipt["partial_field_receipt"]
        self.assertTrue(selection["authority_tiebreak_selected"])
        self.assertEqual(selection["authority_matching_strict_page_count"], 1)
        self.assertEqual(partial["field_accepted_count"], 1)
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertEqual(len(result["candidate_evidence"]), len(CONTROL))

    def test_single_strict_identity_page_needs_no_authority_tiebreak(self) -> None:
        prepared = target.prepare_record_proposal(question("unlisted source"), COLUMNS, (DOCS,))
        result = target.build_representation(
            prepared,
            proposal(),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        selection = result["content_free_receipt"]["authority_selection_receipt"]
        self.assertTrue(selection["unique_identity_page_selected"])
        self.assertFalse(selection["authority_tiebreak_eligible"])
        self.assertTrue(result["content_free_receipt"]["candidate_evidence_changed"])

    def test_missing_or_multiple_authority_fails_closed_on_multiple_pages(self) -> None:
        for authority in ("unlisted source", "PyPI and GitHub"):
            prepared = target.prepare_record_proposal(question(authority), COLUMNS, (PYPI, DOCS))
            result = target.build_representation(
                prepared,
                proposal(),
                control_evidence=CONTROL,
                model_call_attempted=True,
            )
            selection = result["content_free_receipt"]["authority_selection_receipt"]
            with self.subTest(authority=authority):
                self.assertEqual(selection["selected_page_count"], 0)
                self.assertFalse(result["content_free_receipt"]["candidate_evidence_changed"])
                self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_two_matching_authority_pages_fail_closed(self) -> None:
        second = {
            **PYPI,
            "url": "https://pypi.org/project/Alpha-Kit/index.html",
        }
        prepared = target.prepare_record_proposal(question(), COLUMNS, (PYPI, second))
        result = target.build_representation(
            prepared,
            proposal(),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )
        selection = result["content_free_receipt"]["authority_selection_receipt"]
        self.assertEqual(selection["authority_matching_strict_page_count"], 2)
        self.assertEqual(selection["selected_page_count"], 0)
        self.assertEqual(result["candidate_evidence"], CONTROL)

    def test_non_identity_authority_page_cannot_win(self) -> None:
        unrelated = {
            "title": "Other-Kit · PyPI",
            "url": "https://pypi.org/project/Other-Kit/",
            "content": "Other-Kit\nLatest version: 9.0",
        }
        prepared = target.prepare_record_proposal(question(), COLUMNS, (DOCS, unrelated))
        self.assertEqual(prepared["joint_identity_bound_page_count"], 1)
        self.assertEqual(prepared["pages"][0]["url"], canonicalize_url(DOCS["url"]))

    def test_resealed_selection_credit_or_launch_tamper_fails(self) -> None:
        prepared = target.prepare_record_proposal(question(), COLUMNS, (PYPI, DOCS))
        receipt = target.build_representation(
            prepared,
            proposal(),
            control_evidence=CONTROL,
            model_call_attempted=True,
        )["content_free_receipt"]
        for kind in ("selection", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "selection":
                nested = changed["authority_selection_receipt"]
                nested["selected_page_count"] = 0
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_and_label_blind(self) -> None:
        path = ROOT / "src/deepwide_agent/v25090_visible_authority_partial_field_record.py"
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
