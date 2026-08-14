from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25456_date_bounded_official_rfc_xml_record_candidate as target  # noqa: E402


BASE = (
    "```markdown\n"
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 9000 | Old A | A. Old | Unknown | Unknown | Unknown |\n"
    "| RFC 9001 | Old B | B. Old | Unknown | Unknown | Unknown |\n"
    "| RFC 9002 | Old C | C. Old | Unknown | Unknown | Unknown |\n"
    "| RFC 9003 | Old D | D. Old | Unknown | Unknown | Unknown |\n"
    "```"
)
QUESTION = (
    "Return exactly one table for four visible document identities "
    "<RFCS>RFC 9000; RFC 9001; RFC 9002; RFC 9003</RFCS>. "
    "Columns exactly: RFC | Title | Authors | Status | Stream | Published."
)


def prefix(number: int, *, complete_front: bool = False) -> str:
    close = "</front><middle><section>body</section></middle></rfc>" if complete_front else "<abstract><t>truncated"
    return (
        f'<rfc number="{number}" category="std" submissionType="IETF">'
        "<front>"
        f"<title>Official Title {number}</title>"
        f'<seriesInfo name="RFC" value="{number}" stream="IETF"/>'
        f'<author initials="A." surname="Author{number}"><organization>X</organization></author>'
        '<date month="05" year="2021"/>'
        + close
    )


def page(number: int, **kwargs) -> dict[str, str]:
    return {
        "url": f"https://www.rfc-editor.org/rfc/rfc{number}.xml",
        "content": prefix(number, **kwargs),
    }


class V25456DateBoundedOfficialRfcXmlCandidateTests(unittest.TestCase):
    def test_date_bounded_prefix_recovers_all_fields(self) -> None:
        record = target.parse_page(page(9000), 9000)
        self.assertEqual(
            record,
            {
                "RFC": "RFC 9000",
                "Title": "Official Title 9000",
                "Authors": "A. Author9000",
                "Status": "PROPOSED STANDARD",
                "Stream": "IETF",
                "Published": "May 2021",
            },
        )

    def test_complete_front_remains_supported(self) -> None:
        self.assertIsNotNone(target.parse_page(page(9000, complete_front=True), 9000))

    def test_candidate_applies_four_date_bounded_records(self) -> None:
        pages = [page(number) for number in range(9000, 9004)]
        value = target.build_candidate(BASE, question=QUESTION, pages=pages)
        self.assertEqual(value["valid_record_count"], 4)
        self.assertEqual(value["applied_coordinate_count"], 20)
        self.assertTrue(value["candidate_prediction_changed"])
        self.assertIn("Official Title 9003", value["candidate_prediction"])
        self.assertEqual(target.validate_candidate(value, pages=pages), value)

    def test_doctype_entity_incomplete_date_or_author_fail_closed(self) -> None:
        valid = prefix(9000)
        for content in (
            "<!DOCTYPE rfc>" + valid,
            "<!ENTITY x 'y'>" + valid,
            valid.replace(
                '<date month="05" year="2021"/>', '<date month="05"'
            ),
            valid.replace("</author>", ""),
        ):
            changed = page(9000)
            changed["content"] = content
            with self.subTest(content=content[:32]):
                self.assertIsNone(target.parse_page(changed, 9000))

    def test_url_root_series_and_base_binding_still_fail_closed(self) -> None:
        for kind in ("url", "root", "series"):
            changed = page(9000)
            if kind == "url":
                changed["url"] = "https://www.rfc-editor.org/rfc/rfc9001.xml"
            elif kind == "root":
                changed["content"] = changed["content"].replace(
                    'number="9000"', 'number="9001"', 1
                )
            else:
                changed["content"] = changed["content"].replace(
                    'value="9000"', 'value="9001"'
                )
            with self.subTest(kind=kind):
                self.assertIsNone(target.parse_page(changed, 9000))

    def test_resealed_candidate_or_receipt_tamper_fails(self) -> None:
        pages = [page(number) for number in range(9000, 9004)]
        value = target.build_candidate(BASE, question=QUESTION, pages=pages)
        for kind in ("candidate", "receipt"):
            changed = copy.deepcopy(value)
            if kind == "candidate":
                changed["candidate_prediction"] = BASE
            else:
                changed["content_free_receipt"]["valid_record_count"] = 3
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_candidate(changed, pages=pages)

    def test_runtime_is_pure_label_blind_and_launch_forbidden(self) -> None:
        contract = target.integration_contract()
        self.assertTrue(contract["date_bounded_temporary_front_closure_supported"])
        self.assertFalse(contract["benchmark_launch_or_evaluator_authorized"])
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "socket", "requests", "httpx"}
            )
        )

    def test_frozen_v25454_pages_replay_78_of_78_without_truth(self) -> None:
        rows = [
            json.loads(line)
            for line in (
                ROOT
                / "outputs/v25454_official_rfc_xml_shared_effect_external_v1_20260814/frozen_task_results.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        pages = [
            page
            for row in rows
            for page in row["runtime_result"][
                "private_same_forward_official_rfc_xml_pages"
            ]
        ]
        self.assertEqual(len(pages), 78)
        self.assertEqual(
            sum(
                target.parse_page(
                    page,
                    int(page["url"].removesuffix(".xml").rsplit("rfc", 1)[1]),
                )
                is not None
                for page in pages
            ),
            78,
        )


if __name__ == "__main__":
    unittest.main()
