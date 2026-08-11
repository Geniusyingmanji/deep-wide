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

from deepwide_agent import (  # noqa: E402
    v25061_pure_version_qualified_late_record as parent,
)
from deepwide_agent import v25062_prefix_salient_atomic_record as target  # noqa: E402


QUESTION = (
    "Using only the supplied public crate detail page, identify the crate and "
    "return exactly one Markdown table and no prose. Include exactly one row. "
    "Columns must be: Crate | License. Preserve the page's canonical crate "
    "spelling and license value while collapsing whitespace. Use Unknown only "
    "when the supplied page does not establish a value."
)
URL = "https://docs.example.org/crate/async-kit/latest"
TITLE = "async-kit 1.53.1 - Documentation"


def text(
    *,
    license_lines: tuple[str, ...] = ("License", "MIT"),
    license_before_filler: bool = True,
    heading: str = "async-kit-1.53.1",
) -> str:
    prefix = (TITLE, "Documentation portal", heading, "Platform", "x86_64")
    filler = tuple("Long public documentation line." for _ in range(190))
    values = prefix + license_lines + filler if license_before_filler else prefix + filler + license_lines
    return "\n".join(values)


def page(raw: str | None = None, *, title: str = TITLE, url: str = URL) -> dict[str, str]:
    return {"url": url, "title": title, "text": raw or text()}


class V25062PrefixSalientAtomicRecordTests(unittest.TestCase):
    def test_prefix_complete_record_is_atomically_salient_under_same_budget(self) -> None:
        value = target.build_representation(QUESTION, page())
        receipt = value["prefix_salient_atomic_record_receipt"]
        self.assertEqual(receipt["version_qualified_consensus_binding_count"], 1)
        self.assertEqual(receipt["complete_record_count"], 1)
        self.assertEqual(receipt["prefix_complete_record_count"], 1)
        self.assertEqual(receipt["prefix_target_field_count"], 1)
        self.assertEqual(receipt["late_target_field_count"], 0)
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertEqual(len(value["control_evidence"]), 5_000)
        self.assertEqual(len(value["candidate_evidence"]), 5_000)
        self.assertIn('"row":"async-kit"', value["candidate_evidence"])
        self.assertEqual(
            target.extract_record(QUESTION, page()),
            {"Crate": "async-kit", "License": "MIT"},
        )

    def test_late_complete_record_is_excluded_from_salience_mechanism(self) -> None:
        raw_page = page(text(license_before_filler=False))
        value = target.build_representation(QUESTION, raw_page)
        receipt = value["prefix_salient_atomic_record_receipt"]
        self.assertEqual(receipt["complete_record_count"], 1)
        self.assertEqual(receipt["prefix_complete_record_count"], 0)
        self.assertEqual(receipt["late_target_field_count"], 1)
        self.assertFalse(receipt["mechanism_engaged"])
        self.assertEqual(value["candidate_evidence"], value["control_evidence"])
        with self.assertRaises(ValueError):
            target.extract_record(QUESTION, raw_page)

    def test_identity_routes_match_parent_on_prefix_and_late_cases(self) -> None:
        for raw_page in (page(), page(text(license_before_filler=False))):
            with self.subTest(tail=raw_page["text"][-60:]):
                _record, counts, _normalized, _raw = target._complete_prefix_record(
                    QUESTION, raw_page
                )
                parent_value = parent.build_representation(QUESTION, raw_page)
                parent_receipt = parent_value["version_qualified_late_record_receipt"]
                mapping = {
                    "labelled_identity_binding_count": "labelled_identity_binding_count",
                    "exact_consensus_identity_binding_count": "exact_consensus_identity_binding_count",
                    "version_qualified_consensus_binding_count": "version_qualified_consensus_binding_count",
                    "unique_bound_identity_count": "unique_bound_identity_count",
                    "target_detail_candidate_count": "target_detail_candidate_count",
                    "uniquely_bound_target_field_count": "uniquely_bound_target_field_count",
                    "duplicate_or_conflicting_target_count": "duplicate_or_conflicting_target_count",
                    "complete_record_count": "discovered_record_count",
                }
                for child_name, parent_name in mapping.items():
                    self.assertEqual(counts[child_name], parent_receipt[parent_name], child_name)

    def test_exact_and_labelled_parent_routes_remain_available(self) -> None:
        exact_title = "async-kit — Official Documentation"
        exact_text = "\n".join(
            (
                exact_title,
                exact_title,
                "License: MIT",
                *("Long public documentation line." for _ in range(190)),
            )
        )
        exact = target.build_representation(
            QUESTION, page(exact_text, title=exact_title)
        )["prefix_salient_atomic_record_receipt"]
        self.assertEqual(exact["exact_consensus_identity_binding_count"], 1)
        self.assertTrue(exact["mechanism_engaged"])

        labelled_title = "Example Registry: Crate async-kit"
        labelled_text = "\n".join(
            (
                "Crate async-kit",
                "License: MIT",
                *("Long public documentation line." for _ in range(190)),
            )
        )
        labelled = target.build_representation(
            QUESTION, page(labelled_text, title=labelled_title)
        )["prefix_salient_atomic_record_receipt"]
        self.assertEqual(labelled["labelled_identity_binding_count"], 1)
        self.assertTrue(labelled["mechanism_engaged"])

    def test_missing_duplicate_conflicting_unknown_and_mismatch_fail_closed(self) -> None:
        cases = (
            text(license_lines=()),
            text(license_lines=("License: MIT", "License: MIT")),
            text(license_lines=("License: MIT", "License: Apache-2.0")),
            text(license_lines=("License: Unknown",)),
            text(heading="async-kit-1.53.0"),
        )
        for raw in cases:
            with self.subTest(tail=raw[-100:]):
                value = target.build_representation(QUESTION, page(raw))
                self.assertEqual(value["candidate_evidence"], value["control_evidence"])
                self.assertFalse(
                    value["prefix_salient_atomic_record_receipt"]["mechanism_engaged"]
                )

    def test_short_page_and_capacity_failure_hand_off_exactly(self) -> None:
        raw = "\n".join((TITLE, "async-kit-1.53.1", "License: MIT"))
        value = target.build_representation(QUESTION, page(raw))
        receipt = value["prefix_salient_atomic_record_receipt"]
        self.assertEqual(receipt["prefix_complete_record_count"], 1)
        self.assertEqual(receipt["compact_capacity_failure_count"], 1)
        self.assertFalse(receipt["mechanism_engaged"])
        self.assertEqual(value["candidate_evidence"], raw)

    def test_receipt_is_content_free_credit_zero_and_resealed_tamper_fails(self) -> None:
        value = target.build_representation(QUESTION, page())
        receipt = value["prefix_salient_atomic_record_receipt"]
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
        nested = changed["prefix_salient_atomic_record_receipt"]
        nested["prefix_complete_record_count"] = 0
        nested.pop("receipt_payload_sha256")
        nested["receipt_payload_sha256"] = parent.payload_sha256(nested)
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = parent.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_representation(changed, question=QUESTION, page=page())

    def test_extra_privileged_metadata_fails_closed(self) -> None:
        value = target.build_representation(QUESTION, page())
        value["question_type"] = "forbidden"
        value.pop("artifact_payload_sha256")
        value["artifact_payload_sha256"] = parent.payload_sha256(value)
        with self.assertRaises(ValueError):
            target.validate_representation(value, question=QUESTION, page=page())

    def test_module_has_capability_small_imports_and_no_forbidden_literals(self) -> None:
        path = ROOT / "src/deepwide_agent/v25062_prefix_salient_atomic_record.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
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
            "native_search",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden in (
            "benchmark_question_type",
            "answer_key",
            "results.csv",
            "ground_truth",
            "search_many(",
            ".complete(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
