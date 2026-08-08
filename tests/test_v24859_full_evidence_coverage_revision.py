from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24859_full_evidence_coverage_revision import (  # noqa: E402
    EvidencePage,
    apply_full_evidence_revision,
    payload_sha256,
    validate_receipt,
)


BASELINE = """```markdown
| Name | Year | City |
| --- | --- | --- |
| Alpha | Unknown | Paris |
```"""


def table(*rows: tuple[str, str, str]) -> str:
    return (
        "```markdown\n| Name | Year | City |\n| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def page(index: int, content: str, domain: str | None = None) -> dict[str, object]:
    return {
        "evidence_id": f"E{index:04d}",
        "url": f"https://{domain or f'h{index}.example'}/record",
        "content": content,
        "fetch_integrity": True,
    }


class V24859FullEvidenceCoverageRevisionTests(unittest.TestCase):
    def test_two_sources_fill_unknown_without_entropy_routing(self) -> None:
        pages = [
            page(index, "Alpha record. Year: 2025. City: Paris.")
            for index in (1, 2)
        ]
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=pages,
        )
        self.assertIn("| Alpha | 2025 | Paris |", value["candidate_table"])
        receipt = validate_receipt(value["receipt"])
        self.assertEqual(receipt["admitted_existing_unknown_fills"], 1)
        self.assertGreater(receipt["shadow_information_gain_nats"], 0)
        self.assertFalse(receipt["entropy_or_information_gain_used_for_admission"])

    def test_known_override_requires_three_independent_sources(self) -> None:
        proposed = table(("Alpha", "2025", "Lyon"))
        two = [
            page(index, "Alpha record. City: Lyon. Year: 2025.")
            for index in (1, 2)
        ]
        rejected = apply_full_evidence_revision(
            baseline=BASELINE, proposed=proposed, pages=two
        )
        self.assertIn("| Alpha | 2025 | Paris |", rejected["candidate_table"])
        self.assertEqual(
            rejected["receipt"]["admitted_existing_overrides"], 0
        )
        admitted = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=proposed,
            pages=two + [page(3, "Alpha record. City: Lyon. Year: 2025.")],
        )
        self.assertIn("| Alpha | 2025 | Lyon |", admitted["candidate_table"])
        self.assertEqual(admitted["receipt"]["admitted_existing_overrides"], 1)

    def test_complete_new_row_requires_two_sources_for_every_cell(self) -> None:
        pages = [
            page(index, "Beta record. Year: 2024. City: Rome.")
            for index in (1, 2)
        ]
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(
                ("Alpha", "Unknown", "Paris"),
                ("Beta", "2024", "Rome"),
            ),
            pages=pages,
        )
        self.assertIn("| Beta | 2024 | Rome |", value["candidate_table"])
        self.assertEqual(value["receipt"]["admitted_new_rows"], 1)
        self.assertEqual(value["receipt"]["final_row_count"], 2)

    def test_partial_new_row_is_rejected_atomically(self) -> None:
        pages = [
            page(1, "Beta record. Year: 2024. City: Rome."),
            page(2, "Beta record. Year: 2024."),
        ]
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(
                ("Alpha", "Unknown", "Paris"),
                ("Beta", "2024", "Rome"),
            ),
            pages=pages,
        )
        self.assertNotIn("| Beta |", value["candidate_table"])
        self.assertEqual(value["receipt"]["admitted_new_rows"], 0)
        self.assertEqual(value["receipt"]["rejected_partial_new_rows"], 1)

    def test_subdomains_of_one_registrable_domain_are_not_independent(self) -> None:
        pages = [
            page(1, "Alpha record. Year: 2025.", "a.shared.example"),
            page(2, "Alpha record. Year: 2025.", "b.shared.example"),
        ]
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=pages,
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])
        self.assertTrue(value["receipt"]["candidate_identity_handoff"])

    def test_adjacent_markdown_row_cannot_lend_cell_support(self) -> None:
        source = """| Name | Year | City |
| --- | --- | --- |
| Alpha | Unknown | Paris |
| Beta | 2025 | Rome |"""
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[page(index, source) for index in (1, 2)],
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])

    def test_markdown_header_and_same_row_bind_cell_support(self) -> None:
        source = """| Name | Year | City |
| --- | --- | --- |
| Alpha | 2025 | Paris |
| Beta | 2024 | Rome |"""
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[page(index, source) for index in (1, 2)],
        )
        self.assertIn("| Alpha | 2025 | Paris |", value["candidate_table"])

    def test_numeric_and_row_key_substrings_do_not_match(self) -> None:
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[
                page(index, "Alphabet record. Year: 20250. City: Paris.")
                for index in (1, 2)
            ],
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])

    def test_missing_fetch_integrity_is_not_implicitly_trusted(self) -> None:
        pages = [page(index, "Alpha record. Year: 2025.") for index in (1, 2)]
        for item in pages:
            item.pop("fetch_integrity")
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=pages,
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])

    def test_numeric_hosts_are_not_independent_sources(self) -> None:
        pages = [page(index, "Alpha record. Year: 2025.") for index in (1, 2)]
        pages[0]["url"] = "https://192.0.2.1/record"
        with self.assertRaises(ValueError):
            apply_full_evidence_revision(
                baseline=BASELINE,
                proposed=table(("Alpha", "2025", "Paris")),
                pages=pages,
            )

    def test_dataclass_fetch_integrity_defaults_fail_closed(self) -> None:
        pages = [
            EvidencePage(
                evidence_id=f"E{index:04d}",
                url=f"https://h{index}.example/record",
                content="Alpha record. Year: 2025.",
            )
            for index in (1, 2)
        ]
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=pages,
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])

    def test_distant_prose_field_cannot_lend_support(self) -> None:
        source = "Alpha record. " + ("unrelated filler " * 40) + "Year: 2025."
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[page(index, source) for index in (1, 2)],
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])

    def test_duplicate_candidate_row_key_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            apply_full_evidence_revision(
                baseline=BASELINE,
                proposed=table(
                    ("Alpha", "2025", "Paris"),
                    (" alpha ", "2024", "Lyon"),
                ),
                pages=[],
            )

    def test_baseline_rows_cannot_be_deleted(self) -> None:
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Beta", "2024", "Rome")),
            pages=[
                page(index, "Beta record. Year: 2024. City: Rome.")
                for index in (1, 2)
            ],
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])
        self.assertEqual(value["receipt"]["baseline_rows_deleted"], 0)

    def test_model_declared_evidence_membership_is_never_an_input(self) -> None:
        signature = ast.parse(
            (SRC / "deepwide_agent/v24859_full_evidence_coverage_revision.py")
            .read_text(encoding="utf-8")
        )
        function = next(
            node
            for node in signature.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "apply_full_evidence_revision"
        )
        names = [argument.arg for argument in function.args.kwonlyargs]
        self.assertEqual(names, ["baseline", "proposed", "pages"])

    def test_receipt_is_content_free_and_label_blind(self) -> None:
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[
                page(index, "Alpha record. Year: 2025. City: Paris.")
                for index in (1, 2)
            ],
        )
        encoded = json.dumps(value["receipt"], sort_keys=True)
        for prohibited in ("Alpha", "2025", "Paris", "https://", "E0001"):
            self.assertNotIn(prohibited, encoded)
        self.assertFalse(
            value["receipt"]
            ["mapping_gold_category_question_type_split_evaluator_score_or_reward_read"]
        )

    def test_resealed_tamper_fails_conservation(self) -> None:
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[
                page(index, "Alpha record. Year: 2025. City: Paris.")
                for index in (1, 2)
            ],
        )
        altered = copy.deepcopy(value["receipt"])
        altered["admitted_new_rows"] += 1
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_resealed_below_threshold_admission_fails(self) -> None:
        value = apply_full_evidence_revision(
            baseline=BASELINE,
            proposed=table(("Alpha", "2025", "Paris")),
            pages=[
                page(index, "Alpha record. Year: 2025. City: Paris.")
                for index in (1, 2)
            ],
        )
        altered = copy.deepcopy(value["receipt"])
        altered["admitted_support_source_count_distribution"] = {"1": 1}
        altered[
            "admitted_unknown_fill_support_source_count_distribution"
        ] = {"1": 1}
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_runtime_source_has_no_io_model_or_evaluator_capability(self) -> None:
        path = SRC / "deepwide_agent/v24859_full_evidence_coverage_revision.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        relative_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level
        ]
        self.assertEqual(relative_imports, [])
        self.assertTrue(
            imports.issubset(
                {
                    "__future__",
                    "collections",
                    "copy",
                    "dataclasses",
                    "hashlib",
                    "ipaddress",
                    "json",
                    "math",
                    "re",
                    "typing",
                    "unicodedata",
                    "urllib",
                }
            )
        )
        self.assertTrue(
            imports.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "subprocess",
                    "requests",
                    "socket",
                    "evaluator",
                }
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})
        )


if __name__ == "__main__":
    unittest.main()
