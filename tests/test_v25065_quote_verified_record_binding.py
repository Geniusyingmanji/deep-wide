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

from deepwide_agent import v25065_quote_verified_record_binding as target  # noqa: E402


QUESTION = (
    "Use public sources and return a table with columns Entity, Release date, "
    "and License. Preserve repeated entities when they denote distinct records."
)
COLUMNS = ("Entity", "Release date", "License")
PAGES = [
    {
        "title": "Alpha releases",
        "url": "https://example.org/alpha",
        "content": (
            "Alpha release 1. Release date: 2026-01-02. License: MIT. "
            "Alpha release 2. Release date: 2026-02-03. License: Apache-2.0."
        ),
    },
    {
        "title": "Beta record",
        "url": "https://example.net/beta",
        "content": "Beta package. Released: 2025-12-01. License type: BSD-3-Clause.",
    },
]


def proposal(records):
    return json.dumps({"records": records}, ensure_ascii=False)


def record(page, quote, identity, fields):
    return {
        "page_ordinal": page,
        "quote": quote,
        "row_identity": identity,
        "fields": fields,
    }


def field(column, source, value):
    return {"column": column, "source_field": source, "value": value}


class QuoteVerifiedRecordBindingTests(unittest.TestCase):
    def prepared(self):
        return target.prepare_record_proposal(QUESTION, COLUMNS, PAGES)

    def build(self, records, *, control=None):
        return target.build_representation(
            self.prepared(),
            proposal(records),
            control_evidence=control or ("RAW-EVIDENCE " * 2000),
            model_call_attempted=True,
        )

    def test_same_page_quote_identity_field_and_value_are_rendered(self):
        quote = "Alpha release 1. Release date: 2026-01-02. License: MIT."
        value = self.build(
            [
                record(
                    1,
                    quote,
                    "Alpha release 1",
                    [
                        field("Release date", "Release date", "2026-01-02"),
                        field("License", "License", "MIT"),
                    ],
                )
            ]
        )
        receipt = target.validate_receipt(value["content_free_receipt"])
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertEqual(receipt["verified_quote_record_count"], 1)
        self.assertEqual(receipt["rendered_field_count"], 2)
        self.assertEqual(
            receipt["control_evidence_characters"],
            receipt["candidate_evidence_characters"],
        )
        self.assertIn("QUOTE_VERIFIED_RECORD", value["candidate_evidence"])
        self.assertIn("2026-01-02", value["candidate_evidence"])

    def test_deterministic_lexical_source_label_alias_is_allowed(self):
        quote = "Beta package. Released: 2025-12-01. License type: BSD-3-Clause."
        value = self.build(
            [
                record(
                    2,
                    quote,
                    "Beta package",
                    [
                        field("Release date", "Released", "2025-12-01"),
                        field("License", "License type", "BSD-3-Clause"),
                    ],
                )
            ]
        )
        self.assertTrue(value["content_free_receipt"]["candidate_evidence_changed"])

    def test_cross_page_or_paraphrased_quote_fails_closed(self):
        for quote in (
            "Alpha release 1. Released: 2025-12-01.",
            "Alpha release one. Release date: 2026-01-02. License: MIT.",
        ):
            value = self.build(
                [
                    record(
                        1,
                        quote,
                        "Alpha release 1",
                        [field("License", "License", "MIT")],
                    )
                ]
            )
            with self.subTest(quote=quote):
                receipt = value["content_free_receipt"]
                self.assertFalse(receipt["candidate_evidence_changed"])
                self.assertEqual(receipt["verified_quote_record_count"], 0)
                self.assertEqual(
                    value["candidate_evidence"], "RAW-EVIDENCE " * 2000
                )

    def test_missing_identity_source_field_or_value_fails_closed(self):
        quote = "Alpha release 1. Release date: 2026-01-02. License: MIT."
        cases = (
            ("Gamma", field("License", "License", "MIT")),
            ("Alpha release 1", field("License", "Terms", "MIT")),
            ("Alpha release 1", field("License", "License", "GPL")),
            ("Alpha release 1", field("Release date", "License", "MIT")),
        )
        for identity, binding in cases:
            value = self.build([record(1, quote, identity, [binding])])
            with self.subTest(identity=identity, binding=binding):
                self.assertFalse(
                    value["content_free_receipt"]["candidate_evidence_changed"]
                )

    def test_source_label_must_match_exactly_one_visible_target_column(self):
        columns = ("Entity", "Release", "Release date")
        quote = "Alpha release 1. Release: 2026-01-02."
        prepared = target.prepare_record_proposal(
            QUESTION,
            columns,
            [
                {
                    "title": "Ambiguous schema",
                    "url": "https://example.org/ambiguous",
                    "content": quote,
                }
            ],
        )
        value = target.build_representation(
            prepared,
            proposal(
                [
                    record(
                        1,
                        quote,
                        "Alpha release 1",
                        [field("Release", "Release", "2026-01-02")],
                    )
                ]
            ),
            control_evidence="control " * 1000,
            model_call_attempted=True,
        )
        self.assertFalse(value["content_free_receipt"]["candidate_evidence_changed"])
        self.assertEqual(value["content_free_receipt"]["rejected_field_binding_count"], 1)

    def test_nonunique_quote_coordinate_fails_closed(self):
        pages = [
            {
                "title": "Repeated",
                "url": "https://example.edu/repeat",
                "content": "Alpha License: MIT. divider Alpha License: MIT.",
            }
        ]
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
        value = target.build_representation(
            prepared,
            proposal(
                [
                    record(
                        1,
                        "Alpha License: MIT.",
                        "Alpha",
                        [field("License", "License", "MIT")],
                    )
                ]
            ),
            control_evidence="control " * 1000,
            model_call_attempted=True,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["rejected_nonunique_or_nonverbatim_quote_count"], 1)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_ascii_value_must_respect_token_boundaries(self):
        quote = "Alpha release 1. License: LIMITLESS."
        pages = [
            {"title": "Boundary", "url": "https://example.org/b", "content": quote}
        ]
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
        value = target.build_representation(
            prepared,
            proposal(
                [
                    record(
                        1,
                        quote,
                        "Alpha release 1",
                        [field("License", "License", "MIT")],
                    )
                ]
            ),
            control_evidence="raw " * 1000,
            model_call_attempted=True,
        )
        self.assertFalse(value["content_free_receipt"]["candidate_evidence_changed"])

    def test_repeated_identity_at_distinct_quotes_is_not_deduplicated(self):
        first = "Alpha release 1. Release date: 2026-01-02. License: MIT."
        second = "Alpha release 2. Release date: 2026-02-03. License: Apache-2.0."
        value = self.build(
            [
                record(
                    1,
                    first,
                    "Alpha",
                    [field("License", "License", "MIT")],
                ),
                record(
                    1,
                    second,
                    "Alpha",
                    [field("License", "License", "Apache-2.0")],
                ),
            ]
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["verified_quote_record_count"], 2)
        self.assertEqual(receipt["rendered_record_count"], 2)
        self.assertIn("MIT", value["candidate_evidence"])
        self.assertIn("Apache-2.0", value["candidate_evidence"])

    def test_conflict_at_same_quote_coordinate_fails_closed(self):
        quote = "Alpha release 1. Release date: 2026-01-02 or 2026-01-03. License: MIT."
        pages = [
            {"title": "Conflict", "url": "https://example.com/c", "content": quote}
        ]
        prepared = target.prepare_record_proposal(QUESTION, COLUMNS, pages)
        output = proposal(
            [
                record(
                    1,
                    quote,
                    "Alpha release 1",
                    [field("Release date", "Release date", "2026-01-02")],
                ),
                record(
                    1,
                    quote,
                    "Alpha release 1",
                    [field("Release date", "Release date", "2026-01-03")],
                ),
            ]
        )
        value = target.build_representation(
            prepared,
            output,
            control_evidence="raw " * 2000,
            model_call_attempted=True,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["ambiguous_same_quote_record_count"], 1)
        self.assertEqual(receipt["verified_quote_record_count"], 0)
        self.assertFalse(receipt["candidate_evidence_changed"])

    def test_invalid_json_or_unattempted_model_is_exact_identity_handoff(self):
        control = "control bytes " * 100
        for output, attempted in (("not-json", True), ("", False)):
            value = target.build_representation(
                self.prepared(),
                output,
                control_evidence=control,
                model_call_attempted=attempted,
            )
            with self.subTest(attempted=attempted):
                self.assertEqual(value["candidate_evidence"], control)
                self.assertFalse(
                    value["content_free_receipt"]["candidate_evidence_changed"]
                )
                self.assertFalse(
                    value["content_free_receipt"]["model_output_strictly_valid"]
                )

    def test_short_control_never_splits_or_partially_renders_record(self):
        quote = "Alpha release 1. Release date: 2026-01-02. License: MIT."
        control = "small-control"
        value = self.build(
            [
                record(
                    1,
                    quote,
                    "Alpha release 1",
                    [field("License", "License", "MIT")],
                )
            ],
            control=control,
        )
        self.assertEqual(value["candidate_evidence"], control)
        self.assertEqual(value["content_free_receipt"]["rendered_record_count"], 0)

    def test_receipt_tamper_and_entropy_credit_fail_closed(self):
        value = self.build([])
        for mutation in ("length", "credit", "launch", "extra"):
            changed = copy.deepcopy(value["content_free_receipt"])
            if mutation == "length":
                changed["candidate_evidence_characters"] += 1
            elif mutation == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif mutation == "launch":
                changed["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["record_value"] = "hidden"
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_prompt_marks_pages_untrusted_and_forbids_answering(self):
        prepared = self.prepared()
        self.assertIn("untrusted factual data", prepared["system"])
        self.assertIn("Do not answer", prepared["system"])
        self.assertIn("Never splice", prepared["system"])

    def test_module_is_pure_and_ast_label_blind(self):
        path = ROOT / "src/deepwide_agent/v25065_quote_verified_record_binding.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged_subscripts: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
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
                    privileged_subscripts.append(str(node.slice.value))
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "urllib.request",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged_subscripts, [])


if __name__ == "__main__":
    unittest.main()
