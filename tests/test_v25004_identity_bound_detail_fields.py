from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25004_identity_bound_detail_fields as target  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import payload_sha256  # noqa: E402


QUESTION = (
    "Use web search and the official Acme Package Index public page to return "
    "exactly one Markdown table. Include exactly one row for the visible package "
    "identity <PACKAGE>AlphaKit</PACKAGE>. Column names: Package, Version, "
    "Published, License."
)
URL = "https://packages.acme.example/web/packages/AlphaKit/index.html"


def page(text: str | None = None, *, url: str = URL, title: str = "Acme: Package AlphaKit"):
    return {
        "title": title,
        "url": url,
        "text": text
        or "\n".join(
            (
                "Acme: Package AlphaKit",
                "",
                "AlphaKit: Synthetic package detail",
                "",
                "Version: | 2.4.1",
                "Published: | 2026-07-08",
                "License: | Apache-2.0",
                "NeedsCompilation: | no",
                "Documentation follows.",
                *("Additional public documentation line." for _ in range(30)),
            )
        ),
    }


class IdentityBoundDetailFieldTests(unittest.TestCase):
    def test_complete_same_page_detail_record_is_compacted(self) -> None:
        value = target.build_projection(QUESTION, page())
        receipt = value["detail_field_receipt"]
        parent = value["content_free_receipt"]
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(receipt["retained_record_count"], 1)
        self.assertEqual(receipt["retained_bound_observation_count"], 3)
        self.assertEqual(parent["retained_record_count"], 1)
        self.assertEqual(len(value["projection"]), len(page()["text"]))
        self.assertTrue(
            value["projection"].startswith(
                "[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]\n"
            )
        )
        self.assertIn('"row":"AlphaKit"', value["projection"])
        self.assertIn('["Version","2.4.1"]', value["projection"])

    def test_wrong_identity_authority_or_page_surface_falls_back_exactly(self) -> None:
        cases = (
            page(url="https://packages.acme.example/web/packages/Beta/index.html"),
            page(url="https://packages.example/web/packages/AlphaKit/index.html"),
            page(
                title="Unrelated package",
                text="Unrelated\n"
                + "\n".join(page()["text"].splitlines()[8:]),
            ),
        )
        for raw in cases:
            with self.subTest(raw=raw["url"] + raw["title"]):
                value = target.build_projection(QUESTION, raw)
                self.assertEqual(value["projection"], raw["text"][:5_000])
                self.assertTrue(
                    value["detail_field_receipt"]["exact_parent_prefix_handoff"]
                )

        iana_question = QUESTION.replace(
            "Acme Package Index", "IANA Root Zone Database"
        )
        lookalike = page(
            url="https://unrelated.example/root/zone/AlphaKit/index.html"
        )
        value = target.build_projection(iana_question, lookalike)
        self.assertEqual(value["projection"], lookalike["text"][:5_000])

    def test_missing_duplicate_conflicting_or_unknown_field_falls_back(self) -> None:
        base = page()["text"]
        cases = (
            base.replace("License: | Apache-2.0\n", ""),
            base.replace(
                "License: | Apache-2.0",
                "License: | Apache-2.0\nLicense: | Apache-2.0",
            ),
            base.replace(
                "License: | Apache-2.0",
                "License: | Apache-2.0\nLicense: | GPL-3",
            ),
            base.replace("Published: | 2026-07-08", "Published: | Unknown"),
        )
        for text in cases:
            with self.subTest(text=text[-80:]):
                value = target.build_projection(QUESTION, page(text))
                self.assertEqual(value["projection"], text[:5_000])
                self.assertEqual(
                    value["detail_field_receipt"]["retained_record_count"], 0
                )

    def test_exact_heading_and_sentence_fields_are_same_page_bound(self) -> None:
        question = QUESTION.replace(
            "Version, Published, License",
            "Sponsoring Organisation, Registration date, Record last updated",
        )
        text = "\n".join(
            (
                "Acme: Package AlphaKit",
                "Sponsoring Organisation",
                "Acme Registry Corporation",
                "Registration date 2025-01-02.",
                "Record last updated 2026-03-04.",
                *("Additional public documentation line." for _ in range(30)),
            )
        )
        value = target.build_projection(question, page(text))
        receipt = value["detail_field_receipt"]
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(receipt["target_detail_candidate_count"], 3)
        self.assertIn(
            '["Sponsoring Organisation","Acme Registry Corporation"]',
            value["projection"],
        )
        self.assertIn('["Registration date","2025-01-02"]', value["projection"])
        self.assertIn(
            '["Record last updated","2026-03-04"]', value["projection"]
        )

    def test_missing_or_multiple_visible_identity_falls_back(self) -> None:
        questions = (
            QUESTION.replace("<PACKAGE>AlphaKit</PACKAGE>", "AlphaKit"),
            QUESTION.replace(
                "<PACKAGE>AlphaKit</PACKAGE>",
                "<PACKAGE>AlphaKit</PACKAGE> and <PACKAGE>Beta</PACKAGE>",
            ),
        )
        for question in questions:
            value = target.build_projection(question, page())
            self.assertEqual(value["projection"], page()["text"][:5_000])

    def test_no_substring_identity_or_partial_target_label(self) -> None:
        question = QUESTION.replace("AlphaKit", "Alpha")
        value = target.build_projection(question, page())
        self.assertEqual(value["projection"], page()["text"][:5_000])
        partial = page(page()["text"].replace("Published: |", "Publish: |"))
        value = target.build_projection(QUESTION, partial)
        self.assertEqual(value["projection"], partial["text"][:5_000])

    def test_long_page_preserves_exact_5k_output_and_minimum_raw_prefix(self) -> None:
        raw = page(page()["text"] + "\n" + ("Long documentation line.\n" * 500))
        value = target.build_projection(QUESTION, raw)
        receipt = value["detail_field_receipt"]
        self.assertEqual(len(value["projection"]), 5_000)
        self.assertGreaterEqual(receipt["raw_prefix_characters_retained"], 512)
        self.assertEqual(receipt["input_characters_beyond_parent_prefix"], len(raw["text"]) - 5_000)

    def test_content_free_receipt_replay_and_joint_reseal_tamper(self) -> None:
        value = target.build_projection(QUESTION, page())
        self.assertEqual(
            target.validate_projection(value, question=QUESTION, page=page()), value
        )
        text = str(value["detail_field_receipt"])
        for forbidden in ("AlphaKit", "2.4.1", "Apache-2.0", "packages.acme"):
            self.assertNotIn(forbidden, text)
        self.assertFalse(
            value["detail_field_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        tampered = copy.deepcopy(value)
        detail = tampered["detail_field_receipt"]
        detail["retained_bound_observation_count"] = 2
        detail.pop("receipt_payload_sha256")
        detail["receipt_payload_sha256"] = payload_sha256(detail)
        tampered.pop("artifact_payload_sha256")
        tampered["artifact_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_projection(tampered, question=QUESTION, page=page())

    def test_module_has_no_io_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25004_identity_bound_detail_fields.py"
        source_text = path.read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os", "pathlib", "socket", "subprocess", "requests", "deepwidebench"
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key", "benchmark_question_type", "results.csv", "ground_truth"
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
