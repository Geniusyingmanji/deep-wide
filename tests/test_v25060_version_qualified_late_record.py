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

from deepwide_agent import v25060_version_qualified_late_record as target  # noqa: E402
from deepwide_agent.v24980_late_page_bound_projection import (  # noqa: E402
    payload_sha256,
)


QUESTION = (
    "Use the supplied public crate page to identify the row and return exactly "
    "one Markdown table. Column names: Crate, License."
)
URL = "https://docs.example.org/crate/async-kit/latest"


def long_text(
    *,
    title: str = "async-kit 1.53.1 - Documentation",
    heading: str = "async-kit-1.53.1",
    license_lines: tuple[str, ...] = (
        "License",
        "This project is licensed under the MIT license.",
    ),
) -> str:
    return "\n".join(
        (
            title,
            "Documentation portal",
            heading,
            "Platform",
            "x86_64-unknown-linux-gnu",
            *("Long public documentation line." for _ in range(180)),
            *license_lines,
        )
    )


def page(
    text: str | None = None,
    *,
    url: str = URL,
    title: str = "async-kit 1.53.1 - Documentation",
) -> dict[str, str]:
    return {"url": url, "title": title, "text": text or long_text(title=title)}


class V25060VersionQualifiedLateRecordTests(unittest.TestCase):
    def test_version_qualified_two_surface_consensus_admits_late_record(self) -> None:
        self.assertNotIn("async-kit", QUESTION)
        value = target.build_representation(QUESTION, page())
        receipt = value["version_qualified_late_record_receipt"]
        self.assertEqual(receipt["labelled_identity_binding_count"], 0)
        self.assertEqual(receipt["exact_consensus_identity_binding_count"], 0)
        self.assertEqual(receipt["version_qualified_consensus_binding_count"], 1)
        self.assertEqual(receipt["late_target_field_count"], 1)
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(len(value["control_evidence"]), 5_000)
        self.assertEqual(len(value["candidate_evidence"]), 5_000)
        self.assertNotIn("This project is licensed", value["control_evidence"])
        self.assertIn('"row":"async-kit"', value["candidate_evidence"])
        self.assertEqual(
            target.extract_record(QUESTION, page()),
            {"Crate": "async-kit", "License": "This project is licensed under the MIT license."},
        )

    def test_docs_rs_shaped_decoded_surface_is_supported_without_site_name_rule(self) -> None:
        title = "serde 1.0.229 - Docs.rs"
        raw = "\n".join(
            (
                title,
                "Docs.rs",
                "-",
                "serde-1.0.229",
                "-",
                "Platform",
                "x86_64-unknown-linux-gnu",
                *("Public API documentation line." for _ in range(190)),
                "License",
                "Licensed under either of Apache License, Version 2.0 or MIT license.",
            )
        )
        question = (
            "Use this public detail page and return one Markdown table. "
            "Column names: Crate, License."
        )
        raw_page = {
            "url": "https://docs.rs/crate/serde/latest",
            "title": title,
            "text": raw,
        }
        value = target.build_representation(question, raw_page)
        self.assertTrue(
            value["version_qualified_late_record_receipt"]["mechanism_engaged"]
        )
        self.assertEqual(target.extract_record(question, raw_page)["Crate"], "serde")

    def test_version_mismatch_title_echo_only_and_query_identity_reject(self) -> None:
        cases = (
            page(long_text(heading="async-kit-1.53.0")),
            page(
                "\n".join(
                    (
                        "async-kit 1.53.1 - Documentation",
                        *("Long public documentation line." for _ in range(180)),
                        "License",
                        "MIT",
                    )
                )
            ),
            page(url="https://docs.example.org/search?q=async-kit"),
            page(title="Partners of async-kit 1.53.1 - Documentation"),
        )
        for raw in cases:
            with self.subTest(url=raw["url"], title=raw["title"]):
                value = target.build_representation(QUESTION, raw)
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )
                self.assertFalse(
                    value["version_qualified_late_record_receipt"][
                        "mechanism_engaged"
                    ]
                )

    def test_same_name_different_versions_are_not_consensus(self) -> None:
        raw = long_text(heading="async-kit-1.53.1 | async-kit-1.53.0")
        value = target.build_representation(QUESTION, page(raw))
        self.assertEqual(
            value["candidate_evidence"], value["control_evidence"]
        )

    def test_short_page_has_no_information_novelty(self) -> None:
        raw = "\n".join(
            (
                "async-kit 1.53.1 - Documentation",
                "Documentation portal",
                "async-kit-1.53.1",
                "License: MIT",
            )
        )
        value = target.build_representation(QUESTION, page(raw))
        receipt = value["version_qualified_late_record_receipt"]
        self.assertEqual(receipt["discovered_record_count"], 1)
        self.assertEqual(receipt["late_target_field_count"], 0)
        self.assertEqual(receipt["admissible_record_count"], 0)
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])

    def test_exact_v25059_identity_route_is_preserved(self) -> None:
        title = "async-kit — Official Documentation"
        raw = "\n".join(
            (
                title,
                title,
                *("Long public documentation line." for _ in range(180)),
                "License: MIT",
            )
        )
        value = target.build_representation(
            QUESTION, page(raw, title=title)
        )
        receipt = value["version_qualified_late_record_receipt"]
        self.assertEqual(receipt["exact_consensus_identity_binding_count"], 1)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_duplicate_conflicting_or_extra_cell_field_fails_closed(self) -> None:
        cases = (
            long_text(license_lines=("License: MIT", "License: MIT")),
            long_text(license_lines=("License: MIT", "License: Apache-2.0")),
            long_text(license_lines=("License: | MIT | unrelated",)),
            long_text(license_lines=("License: Unknown",)),
        )
        for raw in cases:
            with self.subTest(tail=raw[-100:]):
                value = target.build_representation(QUESTION, page(raw))
                self.assertEqual(
                    value["candidate_evidence"], value["control_evidence"]
                )

    def test_receipt_is_content_free_credit_zero_and_tamper_resistant(self) -> None:
        value = target.build_representation(QUESTION, page())
        receipt = value["version_qualified_late_record_receipt"]
        encoded = str(receipt)
        for forbidden in (
            "async-kit",
            "1.53.1",
            "MIT",
            "docs.example.org",
            "Crate",
            "License",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertFalse(receipt["entropy_or_information_gain_assigns_signed_credit"])

        changed = copy.deepcopy(value)
        nested = changed["version_qualified_late_record_receipt"]
        nested["version_qualified_consensus_binding_count"] = 0
        nested.pop("receipt_payload_sha256")
        nested["receipt_payload_sha256"] = payload_sha256(nested)
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_representation(changed, question=QUESTION, page=page())

        extra = target.build_representation(QUESTION, page())
        extra["question_type"] = "forbidden"
        extra.pop("artifact_payload_sha256")
        extra["artifact_payload_sha256"] = payload_sha256(extra)
        with self.assertRaises(ValueError):
            target.validate_representation(extra, question=QUESTION, page=page())

    def test_module_has_no_effect_or_privileged_imports(self) -> None:
        path = ROOT / "src/deepwide_agent/v25060_version_qualified_late_record.py"
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
