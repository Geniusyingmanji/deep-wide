from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25449_official_rfc_xml_record_candidate as target  # noqa: E402


QUESTION = (
    "Return exactly one table for four visible document identities "
    "<RFCS>RFC 9000; RFC 9001; RFC 9002; RFC 9003</RFCS>. "
    "Columns exactly: RFC | Title | Authors | Status | Stream | Published."
)
BASE = (
    "```markdown\n"
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 9000 | Unknown | Unknown | Unknown | Unknown | Unknown |\n"
    "| RFC 9001 | Unknown | Unknown | Unknown | Unknown | Unknown |\n"
    "| RFC 9002 | Unknown | Unknown | Unknown | Unknown | Unknown |\n"
    "| RFC 9003 | Unknown | Unknown | Unknown | Unknown | Unknown |\n"
    "```"
)


def xml(
    number: int,
    *,
    category: str = "std",
    stream: str = "IETF",
    series: str = "",
    role: str = "",
) -> str:
    extra = f'<seriesInfo name="{series}" value="99" stream="{stream}"/>' if series else ""
    editor = f' role="{role}"' if role else ""
    return (
        f'<rfc number="{number}" category="{category}" submissionType="{stream}">'
        "<front>"
        f"<title>Title {number}</title>"
        f'<seriesInfo name="RFC" value="{number}" stream="{stream}"/>'
        f"{extra}"
        f'<author initials="A." surname="Author{number}"{editor}/>'
        '<date month="08" year="2026"/>'
        "</front><middle><section><name>Body</name></section></middle></rfc>"
    )


def page(number: int, **kwargs) -> dict[str, str]:
    return {
        "url": f"https://www.rfc-editor.org/rfc/rfc{number}.xml",
        "content": xml(number, **kwargs),
    }


class V25449OfficialRfcXmlRecordCandidateTests(unittest.TestCase):
    def test_request_vector_uses_only_strict_visible_membership(self) -> None:
        requests = target.request_vector(QUESTION)
        self.assertEqual(len(requests), 4)
        self.assertEqual(
            [item["url"] for item in requests],
            [
                f"https://www.rfc-editor.org/rfc/rfc{number}.xml"
                for number in range(9000, 9004)
            ],
        )
        self.assertEqual(target.request_vector("RFC 9000 in prose"), [])

    def test_parses_std_bcp_irtf_independent_and_editor(self) -> None:
        cases = (
            (page(9000, category="std", series="STD"), "INTERNET STANDARD", "IETF", "A. Author9000"),
            (page(9001, category="bcp", series="BCP"), "BEST CURRENT PRACTICE", "IETF", "A. Author9001"),
            (page(9002, category="info", stream="IRTF"), "INFORMATIONAL", "IRTF", "A. Author9002"),
            (page(9003, category="exp", stream="independent", role="editor"), "EXPERIMENTAL", "INDEPENDENT", "A. Author9003, Ed."),
        )
        for raw, status, stream, author in cases:
            number = int(raw["url"].split("rfc")[-1].split(".")[0])
            with self.subTest(number=number):
                record = target.parse_page(raw, number)
                self.assertIsNotNone(record)
                self.assertEqual(record["Status"], status)
                self.assertEqual(record["Stream"], stream)
                self.assertEqual(record["Authors"], author)
                self.assertEqual(record["Published"], "August 2026")

    def test_builds_complete_candidate_and_replays(self) -> None:
        pages = [
            page(9000, category="std", series="STD"),
            page(9001, category="bcp", series="BCP"),
            page(9002, category="info", stream="IRTF"),
            page(9003, category="exp", stream="independent"),
        ]
        value = target.build_candidate(BASE, question=QUESTION, pages=pages)
        self.assertEqual(
            target.validate_candidate(value, question=QUESTION, pages=pages), value
        )
        self.assertTrue(value["candidate_prediction_changed"])
        self.assertEqual(value["valid_record_count"], 4)
        self.assertEqual(value["applied_coordinate_count"], 20)
        self.assertIn("| RFC 9000 | Title 9000 |", value["candidate_prediction"])

    def test_partial_missing_or_invalid_page_preserves_corresponding_rows(self) -> None:
        bad = page(9001)
        bad["content"] = bad["content"].replace('number="9001"', 'number="9999"')
        value = target.build_candidate(
            BASE,
            question=QUESTION,
            pages=[page(9000), bad],
        )
        self.assertEqual(value["valid_record_count"], 1)
        self.assertEqual(value["invalid_page_count"], 1)
        self.assertEqual(value["missing_page_count"], 2)
        self.assertIn(
            "| RFC 9001 | Unknown | Unknown | Unknown | Unknown | Unknown |",
            value["candidate_prediction"],
        )

    def test_url_identity_xml_identity_front_series_and_shape_must_agree(self) -> None:
        variants = []
        wrong_url = page(9000)
        wrong_url["url"] = "https://www.rfc-editor.org/rfc/rfc9001.xml"
        variants.append(wrong_url)
        wrong_series = page(9000)
        wrong_series["content"] = wrong_series["content"].replace(
            'name="RFC" value="9000"', 'name="RFC" value="9001"'
        )
        variants.append(wrong_series)
        variants.append({"url": page(9000)["url"], "content": "<rfc>"})
        variants.append(
            {"url": page(9000)["url"], "content": "<!DOCTYPE x [<!ENTITY y SYSTEM 'file:///etc/passwd'>]><rfc number='9000'>&y;</rfc>"}
        )
        for raw in variants:
            with self.subTest(raw=raw["content"][:30]):
                self.assertIsNone(target.parse_page(raw, 9000))

    def test_bounded_prefix_with_complete_front_is_accepted_but_truncation_fails(self) -> None:
        raw = page(9000)
        raw["content"] = raw["content"].replace(
            "</front><middle><section><name>Body</name></section></middle></rfc>",
            "</front><middle>" + "x" * 20_000,
        )[:5_000]
        self.assertIsNotNone(target.parse_page(raw, 9000))
        truncated = copy.deepcopy(raw)
        truncated["content"] = truncated["content"].split("</front>")[0]
        self.assertIsNone(target.parse_page(truncated, 9000))

    def test_noop_and_resealed_tamper_fail_closed(self) -> None:
        exact = BASE.replace("Unknown", "Value")
        value = target.build_candidate(exact, question="no membership", pages=[])
        self.assertFalse(value["candidate_prediction_changed"])
        changed = copy.deepcopy(value)
        changed["positive_signed_credit_count"] = 1
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_candidate(
                changed, question="no membership", pages=[], replay=False
            )

    def test_primitive_is_label_blind_and_effect_free(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["maximum_deterministic_official_xml_requests"], 4)
        self.assertFalse(
            contract["mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"]
        )
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint(
                {"requests", "httpx", "urllib3", "socket", "subprocess", "os"}
            )
        )
        forbidden = {
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "gold",
            "score",
            "reward",
        }
        accessed: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    accessed.add(node.slice.value)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                accessed.add(node.args[0].value)
        self.assertTrue(accessed.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
