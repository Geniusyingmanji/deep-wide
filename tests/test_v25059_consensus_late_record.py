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

from deepwide_agent import v25059_consensus_late_record as target  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import (  # noqa: E402
    payload_sha256,
)


QUESTION = (
    "Use the supplied public project page to identify the row and return exactly "
    "one Markdown table. Column names: Package, Version, Published, License."
)
URL = "https://docs.example.org/projects/AlphaKit/index.html"


def late_text(
    *,
    heading: str = "AlphaKit — Official Documentation",
    fields: tuple[str, ...] = (
        "Version: | 2.4.1",
        "Published: | 2026-07-08",
        "License: | Apache-2.0",
    ),
) -> str:
    return "\n".join(
        (
            heading,
            heading,
            "Public project overview.",
            *("Early navigation and documentation line." for _ in range(180)),
            *fields,
            *("Later public documentation line." for _ in range(40)),
        )
    )


def page(
    text: str | None = None,
    *,
    url: str = URL,
    title: str = "AlphaKit — Official Documentation",
) -> dict[str, str]:
    return {"url": url, "title": title, "text": text or late_text()}


class V25059ConsensusLateRecordTests(unittest.TestCase):
    def test_unlabelled_three_surface_consensus_admits_late_record(self) -> None:
        self.assertNotIn("AlphaKit", QUESTION)
        value = target.build_representation(QUESTION, page())
        receipt = value["consensus_late_record_receipt"]
        self.assertEqual(receipt["labelled_identity_binding_count"], 0)
        self.assertEqual(receipt["consensus_identity_binding_count"], 1)
        self.assertEqual(receipt["unique_bound_identity_count"], 1)
        self.assertEqual(receipt["late_target_field_count"], 3)
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(len(value["control_evidence"]), 5_000)
        self.assertEqual(len(value["candidate_evidence"]), 5_000)
        self.assertNotIn("2.4.1", value["control_evidence"])
        self.assertIn('"row":"AlphaKit"', value["candidate_evidence"])
        self.assertEqual(
            target.extract_record(QUESTION, page()),
            {
                "Package": "AlphaKit",
                "Version": "2.4.1",
                "Published": "2026-07-08",
                "License": "Apache-2.0",
            },
        )

    def test_short_page_with_no_late_information_hands_parent_through(self) -> None:
        raw = page(
            "\n".join(
                (
                    "AlphaKit — Official Documentation",
                    "AlphaKit — Official Documentation",
                    "Version: | 2.4.1",
                    "Published: | 2026-07-08",
                    "License: | Apache-2.0",
                )
            )
        )
        value = target.build_representation(QUESTION, raw)
        receipt = value["consensus_late_record_receipt"]
        self.assertEqual(receipt["discovered_record_count"], 1)
        self.assertEqual(receipt["late_target_field_count"], 0)
        self.assertEqual(receipt["admissible_record_count"], 0)
        self.assertFalse(receipt["mechanism_engaged"])
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])
        with self.assertRaises(ValueError):
            target.extract_record(QUESTION, raw)

    def test_one_late_field_is_minimum_information_novelty_gate(self) -> None:
        raw = "\n".join(
            (
                "AlphaKit — Official Documentation",
                "AlphaKit — Official Documentation",
                "Version: | 2.4.1",
                "Published: | 2026-07-08",
                *("Early navigation and documentation line." for _ in range(180)),
                "License: | Apache-2.0",
            )
        )
        value = target.build_representation(QUESTION, page(raw))
        receipt = value["consensus_late_record_receipt"]
        self.assertEqual(receipt["late_target_field_count"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_parent_sentence_and_heading_value_formats_are_preserved(self) -> None:
        raw = "\n".join(
            (
                "AlphaKit — Official Documentation",
                "AlphaKit — Official Documentation",
                *("Early navigation and documentation line." for _ in range(180)),
                "Version 2.4.1.",
                "Published",
                "2026-07-08",
                "License Apache-2.0.",
            )
        )
        value = target.build_representation(QUESTION, page(raw))
        self.assertTrue(
            value["consensus_late_record_receipt"]["mechanism_engaged"]
        )
        self.assertEqual(
            target.extract_record(QUESTION, page(raw)),
            {
                "Package": "AlphaKit",
                "Version": "2.4.1",
                "Published": "2026-07-08",
                "License": "Apache-2.0",
            },
        )

    def test_title_containment_body_only_or_surface_disagreement_rejects(self) -> None:
        cases = (
            page(title="Partners of AlphaKit and related projects"),
            page(
                late_text(heading="DifferentKit — Official Documentation"),
                title="AlphaKit — Official Documentation",
            ),
            page(
                late_text(heading="AlphaKit — Official Documentation"),
                title="DifferentKit — Official Documentation",
            ),
            page(
                late_text(heading="Documentation Home"),
                title="Documentation Home",
            ),
            page(
                late_text(heading="Official Documentation"),
                url="https://docs.example.org/official-documentation/index.html",
                title="Official Documentation",
            ),
            page(
                late_text(),
                url="https://docs.example.org/search?q=AlphaKit",
            ),
            page(
                "\n".join(
                    (
                        "AlphaKit — Official Documentation",
                        *("Early navigation and documentation line." for _ in range(180)),
                        "Version: | 2.4.1",
                        "Published: | 2026-07-08",
                        "License: | Apache-2.0",
                    )
                )
            ),
        )
        for raw in cases:
            with self.subTest(title=raw["title"]):
                value = target.build_representation(QUESTION, raw)
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )
                self.assertFalse(
                    value["consensus_late_record_receipt"]["mechanism_engaged"]
                )

    def test_two_joint_url_title_heading_candidates_are_ambiguous(self) -> None:
        raw = page(
            late_text(heading="AlphaKit | BetaKit"),
            url="https://docs.example.org/projects/AlphaKit/BetaKit/index.html",
            title="AlphaKit | BetaKit",
        )
        value = target.build_representation(QUESTION, raw)
        receipt = value["consensus_late_record_receipt"]
        self.assertEqual(receipt["consensus_identity_binding_count"], 2)
        self.assertEqual(receipt["unique_bound_identity_count"], 0)
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])

    def test_explicit_labelled_parent_route_remains_available(self) -> None:
        raw = page(
            late_text(heading="Package AlphaKit"),
            title="Example Repository: Package AlphaKit",
        )
        value = target.build_representation(QUESTION, raw)
        receipt = value["consensus_late_record_receipt"]
        self.assertEqual(receipt["labelled_identity_binding_count"], 1)
        self.assertEqual(receipt["unique_bound_identity_count"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_missing_duplicate_conflicting_or_unknown_target_fails_closed(self) -> None:
        base = late_text()
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
            base.replace("Version: | 2.4.1", "Version: | 2.4.1 | unrelated"),
        )
        for text in cases:
            with self.subTest(text=text[-120:]):
                value = target.build_representation(QUESTION, page(text))
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )
                self.assertEqual(
                    value["consensus_late_record_receipt"][
                        "retained_record_count"
                    ],
                    0,
                )

    def test_receipt_is_content_free_and_credit_remains_zero(self) -> None:
        value = target.build_representation(QUESTION, page())
        encoded = str(value["consensus_late_record_receipt"])
        for forbidden in (
            "AlphaKit",
            "2.4.1",
            "Apache-2.0",
            "docs.example.org",
            "Package",
            "Published",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(
            value["consensus_late_record_receipt"][
                "positive_signed_credit_count"
            ],
            0,
        )
        self.assertFalse(
            value["consensus_late_record_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )

    def test_replay_nested_tamper_and_extra_metadata_fail_closed(self) -> None:
        value = target.build_representation(QUESTION, page())
        self.assertEqual(
            target.validate_representation(value, question=QUESTION, page=page()),
            value,
        )
        changed = copy.deepcopy(value)
        receipt = changed["consensus_late_record_receipt"]
        receipt["late_target_field_count"] = 0
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_representation(changed, question=QUESTION, page=page())

        extra = target.build_representation(QUESTION, page())
        extra["category"] = "forbidden"
        extra.pop("artifact_payload_sha256")
        extra["artifact_payload_sha256"] = payload_sha256(extra)
        with self.assertRaises(ValueError):
            target.validate_representation(extra, question=QUESTION, page=page())

    def test_module_has_no_effect_or_privileged_imports(self) -> None:
        path = ROOT / "src/deepwide_agent/v25059_consensus_late_record.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "openai",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "benchmark_question_type",
            "answer_key",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
