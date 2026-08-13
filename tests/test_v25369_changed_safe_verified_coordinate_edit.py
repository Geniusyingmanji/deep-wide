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

from deepwide_agent import (  # noqa: E402
    v25360_quote_coordinate_partial_field_record as verifier,
)
from deepwide_agent import (  # noqa: E402
    v25369_changed_safe_verified_coordinate_edit as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "Use public sources. Columns exactly: Entity | Release date | License | Status."
)
COLUMNS = ("Entity", "Release date", "License", "Status")
QUOTE_ALPHA = (
    "Alpha release. Release date: 2026-01-02. License: MIT. Status: Final."
)
QUOTE_BETA = (
    "Beta release. Release date: 2025-06-03. License: Apache-2.0. Status: Active."
)
PAGES = (
    {"url": "https://example.test/alpha", "title": "Alpha", "content": QUOTE_ALPHA},
    {"url": "https://example.test/beta", "title": "Beta", "content": QUOTE_BETA},
)
BASE = (
    "```markdown\n"
    "| Entity | Release date | License | Status |\n"
    "| --- | --- | --- | --- |\n"
    "| Alpha release | Unknown | BSD | Final |\n"
    "| Beta release | 2025-06-03 | Apache-2.0 | Active |\n"
    "```"
)


def field(column: str, source: str, value: str) -> dict[str, str]:
    return {"column": column, "source_field": source, "value": value}


def record(
    fields,
    *,
    page: int = 1,
    quote: str = QUOTE_ALPHA,
    identity: str = "Alpha release",
):
    return {
        "page_ordinal": page,
        "quote": quote,
        "row_identity": identity,
        "fields": fields,
    }


def run(records, *, base: str = BASE, columns=COLUMNS, pages=PAGES):
    prepared = verifier.prepare_record_proposal(QUESTION, columns, pages)
    return target.apply_changed_safe_verified_coordinates(
        base_prediction=base,
        columns=columns,
        prepared=prepared,
        record_output=json.dumps({"records": records}),
        model_call_attempted=True,
    )


class V25369ChangedSafeVerifiedCoordinateEditTests(unittest.TestCase):
    def test_one_shared_base_table_gets_only_changed_safe_edits(self) -> None:
        value = run(
            [
                record(
                    [
                        field("Release date", "Release date", "2026-01-02"),
                        field("License", "License", "MIT"),
                        field("Status", "Status", "Final"),
                    ]
                )
            ]
        )
        receipt = target.validate_receipt(value["content_free_receipt"])
        self.assertEqual(value["control_prediction"], BASE)
        self.assertIn(
            "| Alpha release | 2026-01-02 | MIT | Final |",
            value["candidate_prediction"],
        )
        self.assertIn(
            "| Beta release | 2025-06-03 | Apache-2.0 | Active |",
            value["candidate_prediction"],
        )
        self.assertEqual(receipt["verified_field_count"], 3)
        self.assertEqual(receipt["changed_safe_coordinate_count"], 2)
        self.assertEqual(receipt["unchanged_verified_coordinate_count"], 1)
        self.assertTrue(receipt["candidate_prediction_changed"])
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_already_matching_value_is_identity_handoff(self) -> None:
        value = run([record([field("Status", "Status", "Final")])])
        receipt = value["content_free_receipt"]
        self.assertEqual(value["candidate_prediction"], BASE)
        self.assertEqual(receipt["unchanged_verified_coordinate_count"], 1)
        self.assertTrue(receipt["candidate_identity_handoff"])

    def test_missing_or_ambiguous_row_is_identity_noop(self) -> None:
        missing_alpha = BASE.replace(
            "| Alpha release | Unknown | BSD | Final |\n",
            "",
        )
        ambiguous = BASE.replace(
            "\n```",
            "\n| Alpha release | 2020-01-01 | GPL | Draft |\n```",
        )
        cases = (
            (
                [record([field("License", "License", "MIT")])],
                missing_alpha,
                "missing_row_rejected_field_count",
            ),
            (
                [record([field("License", "License", "MIT")])],
                ambiguous,
                "ambiguous_row_rejected_field_count",
            ),
        )
        for records, base, counter in cases:
            with self.subTest(counter=counter):
                value = run(records, base=base)
                self.assertEqual(value["candidate_prediction"], base)
                self.assertEqual(value["content_free_receipt"][counter], 1)

    def test_multiple_source_coordinates_are_noop_even_when_values_agree(self) -> None:
        second_quote = "Alpha release metadata. License: MIT. Status: Final."
        pages = (*PAGES, {"url": "https://other.test/alpha", "title": "", "content": second_quote})
        value = run(
            [
                record([field("License", "License", "MIT")]),
                record(
                    [field("License", "License", "MIT")],
                    page=3,
                    quote=second_quote,
                ),
            ],
            pages=pages,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(value["candidate_prediction"], BASE)
        self.assertEqual(
            receipt["multiple_source_coordinate_rejected_field_count"], 2
        )

    def test_cross_source_conflict_is_noop(self) -> None:
        second_quote = "Alpha release metadata. License: GPL. Status: Final."
        pages = (*PAGES, {"url": "https://other.test/alpha", "title": "", "content": second_quote})
        value = run(
            [
                record([field("License", "License", "MIT")]),
                record(
                    [field("License", "License", "GPL")],
                    page=3,
                    quote=second_quote,
                ),
            ],
            pages=pages,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(value["candidate_prediction"], BASE)
        self.assertEqual(
            receipt["conflicting_source_coordinate_rejected_field_count"], 2
        )

    def test_unknown_bad_quote_missing_column_and_noncanonical_table_are_noops(self) -> None:
        cases = (
            (
                [record([field("License", "License", "Unknown")])],
                BASE,
                "verified_field_count",
                0,
            ),
            (
                [record([field("License", "License", "MIT")], quote="not verbatim quote long enough")],
                BASE,
                "verified_field_count",
                0,
            ),
            (
                [record([field("Missing", "License", "MIT")])],
                BASE,
                "verified_field_count",
                0,
            ),
            (
                [record([field("License", "License", "MIT")])],
                BASE.removeprefix("```markdown\n").removesuffix("\n```"),
                "table_or_schema_rejected_field_count",
                1,
            ),
        )
        for records, base, counter, expected in cases:
            with self.subTest(counter=counter, base=base[:12]):
                value = run(records, base=base)
                self.assertEqual(value["candidate_prediction"], base)
                self.assertEqual(value["content_free_receipt"][counter], expected)

    def test_resealed_count_credit_or_authorization_tamper_fails(self) -> None:
        receipt = run([record([field("License", "License", "MIT")])])[
            "content_free_receipt"
        ]
        for kind in ("count", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "count":
                changed["changed_safe_coordinate_count"] += 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_label_blind_and_has_no_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25369_changed_safe_verified_coordinate_edit.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
