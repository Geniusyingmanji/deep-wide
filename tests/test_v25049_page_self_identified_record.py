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

from deepwide_agent import v25049_page_self_identified_record as target  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import payload_sha256  # noqa: E402


QUESTION = (
    "Use the supplied public package page to identify the row and return exactly "
    "one Markdown table. Column names: Package, Version, Published, License."
)
URL = "https://packages.example.org/web/packages/AlphaKit/index.html"


def page(
    text: str | None = None,
    *,
    url: str = URL,
    title: str = "Example Repository: Package AlphaKit",
) -> dict[str, str]:
    return {
        "title": title,
        "url": url,
        "text": text
        or "\n".join(
            (
                "Package AlphaKit",
                "A synthetic package detail page.",
                *("Early public navigation and documentation line." for _ in range(180)),
                "Version: | 2.4.1",
                "Published: | 2026-07-08",
                "License: | Apache-2.0",
                *("Long public documentation line." for _ in range(120)),
            )
        ),
    }


class PageSelfIdentifiedRecordTests(unittest.TestCase):
    def test_page_discovers_identity_not_enumerated_by_question(self) -> None:
        self.assertNotIn("AlphaKit", QUESTION)
        value = target.build_representation(QUESTION, page())
        receipt = value["page_self_record_receipt"]
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(receipt["jointly_bound_identity_count"], 1)
        self.assertEqual(receipt["retained_record_count"], 1)
        self.assertEqual(receipt["retained_bound_observation_count"], 3)
        self.assertEqual(len(value["control_evidence"]), 5_000)
        self.assertEqual(len(value["candidate_evidence"]), 5_000)
        self.assertNotIn("2.4.1", value["control_evidence"][:200])
        self.assertIn('"row":"AlphaKit"', value["candidate_evidence"])
        self.assertIn('["Published","2026-07-08"]', value["candidate_evidence"])

    def test_exact_row_label_field_can_supply_second_surface(self) -> None:
        raw = page(
            "\n".join(
                (
                    "Repository package details",
                    "Package: | AlphaKit",
                    "Version: | 2.4.1",
                    "Published: | 2026-07-08",
                    "License: | Apache-2.0",
                    *("Long public documentation line." for _ in range(300)),
                )
            )
        )
        value = target.build_representation(QUESTION, raw)
        receipt = value["page_self_record_receipt"]
        self.assertGreaterEqual(receipt["leading_identity_candidate_count"], 1)
        self.assertEqual(receipt["row_label_identity_candidate_count"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_wrong_url_or_missing_title_binding_falls_back_exactly(self) -> None:
        cases = (
            page(url="https://packages.example.org/web/packages/Beta/index.html"),
            page(title="Example Repository package details"),
        )
        for raw in cases:
            with self.subTest(raw=raw["url"] + raw["title"]):
                value = target.build_representation(QUESTION, raw)
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )
                self.assertTrue(
                    value["page_self_record_receipt"]["exact_parent_prefix_handoff"]
                )

    def test_title_leading_identity_disagreement_fails_closed(self) -> None:
        raw = page(page()["text"].replace("Package AlphaKit", "Package Beta", 1))
        value = target.build_representation(QUESTION, raw)
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])
        self.assertEqual(
            value["page_self_record_receipt"]["jointly_bound_identity_count"], 0
        )

    def test_missing_duplicate_conflicting_or_unknown_target_falls_back(self) -> None:
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
            with self.subTest(text=text[:80]):
                value = target.build_representation(QUESTION, page(text))
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )
                self.assertEqual(
                    value["page_self_record_receipt"]["retained_record_count"], 0
                )

    def test_no_schema_or_short_page_falls_back_without_padding(self) -> None:
        no_schema = target.build_representation("Return a table.", page())
        self.assertEqual(no_schema["candidate_evidence"], no_schema["control_evidence"])
        short = page("Package AlphaKit\nVersion: | 2.4.1\nPublished: | 2026-07-08\nLicense: | MIT")
        value = target.build_representation(QUESTION, short)
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])
        self.assertEqual(len(value["candidate_evidence"]), len(short["text"]))

    def test_receipt_is_content_free_and_credit_remains_zero(self) -> None:
        value = target.build_representation(QUESTION, page())
        encoded = str(value["page_self_record_receipt"])
        for forbidden in (
            "AlphaKit", "2.4.1", "Apache-2.0", "packages.example.org",
            "Package", "Published",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["page_self_record_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        self.assertEqual(
            value["page_self_record_receipt"]["positive_signed_credit_count"], 0
        )

    def test_replay_and_nested_reseal_tamper_fail_closed(self) -> None:
        value = target.build_representation(QUESTION, page())
        self.assertEqual(
            target.validate_representation(value, question=QUESTION, page=page()),
            value,
        )
        changed = copy.deepcopy(value)
        receipt = changed["page_self_record_receipt"]
        receipt["jointly_bound_identity_count"] = 0
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_representation(changed, question=QUESTION, page=page())

    def test_extra_metadata_fails_closed(self) -> None:
        value = target.build_representation(QUESTION, page())
        value["category"] = "forbidden"
        value["artifact_payload_sha256"] = payload_sha256(
            {key: item for key, item in value.items() if key != "artifact_payload_sha256"}
        )
        with self.assertRaises(ValueError):
            target.validate_representation(value, question=QUESTION, page=page())

    def test_module_has_no_effect_or_privileged_imports(self) -> None:
        path = ROOT / "src/deepwide_agent/v25049_page_self_identified_record.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os", "pathlib", "socket", "subprocess", "requests", "deepwidebench"
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden in (
            "benchmark_question_type", "answer_key", "results.csv", "ground_truth"
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
