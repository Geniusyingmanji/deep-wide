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

from deepwide_agent import v25289_monotone_unknown_fill as target  # noqa: E402
from deepwide_agent.v24859_full_evidence_coverage_revision import payload_sha256  # noqa: E402


BASELINE = """```markdown
| Name | Year | City |
| --- | --- | --- |
| Alpha | Unknown | Paris |
| Beta | 2024 | Unknown |
```"""


def table(*rows: tuple[str, str, str]) -> str:
    return (
        "```markdown\n| Name | Year | City |\n| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def page(index: int, content: str, *, integrity: bool = True) -> dict[str, object]:
    return {
        "evidence_id": f"E{index:04d}",
        "url": f"https://source{index}.example/record",
        "content": content,
        "fetch_integrity": integrity,
    }


def proposal(alpha_year: str = "2025", beta_city: str = "Rome") -> str:
    return table(
        ("Alpha", alpha_year, "Paris"),
        ("Beta", "2024", beta_city),
    )


class V25289MonotoneUnknownFillTests(unittest.TestCase):
    def test_one_same_forward_page_can_fill_unknown(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(alpha_year="2025", beta_city="Unknown"),
            pages=[page(1, "Alpha record. Year: 2025. City: Paris.")],
        )
        self.assertIn("| Alpha | 2025 | Paris |", value["candidate_table"])
        receipt = target.validate_receipt(value["receipt"])
        self.assertEqual(receipt["proposed_unknown_fill_count"], 1)
        self.assertEqual(receipt["admitted_unknown_fill_count"], 1)
        self.assertTrue(receipt["prediction_changed"])
        self.assertGreater(receipt["shadow_information_gain_nats"], 0)
        self.assertFalse(
            receipt["entropy_or_information_gain_used_for_admission_or_credit_sign"]
        )

    def test_multiple_supported_unknowns_fill_monotonically(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(),
            pages=[
                page(1, "Alpha record. Year: 2025. City: Paris."),
                page(2, "Beta record. Year: 2024. City: Rome."),
            ],
        )
        self.assertIn("| Alpha | 2025 | Paris |", value["candidate_table"])
        self.assertIn("| Beta | 2024 | Rome |", value["candidate_table"])
        self.assertEqual(value["receipt"]["admitted_unknown_fill_count"], 2)

    def test_known_cell_change_rejects_whole_proposal(self) -> None:
        changed = table(
            ("Alpha", "2025", "Lyon"),
            ("Beta", "2024", "Rome"),
        )
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=changed,
            pages=[
                page(1, "Alpha record. Year: 2025. City: Lyon."),
                page(2, "Beta record. Year: 2024. City: Rome."),
            ],
        )
        self.assertEqual(value["candidate_table"], BASELINE)
        self.assertEqual(
            value["receipt"]["forbidden_known_cell_change_count"], 1
        )
        self.assertEqual(
            value["receipt"]["rejected_by_whole_proposal_count"], 2
        )

    def test_row_reorder_addition_or_deletion_rejects_whole_proposal(self) -> None:
        candidates = (
            table(("Beta", "2024", "Rome"), ("Alpha", "2025", "Paris")),
            table(
                ("Alpha", "2025", "Paris"),
                ("Beta", "2024", "Rome"),
                ("Gamma", "2023", "Oslo"),
            ),
            table(("Alpha", "2025", "Paris")),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                value = target.apply_monotone_unknown_fill(
                    baseline=BASELINE,
                    proposed=candidate,
                    pages=[],
                )
                self.assertEqual(value["candidate_table"], BASELINE)
                self.assertFalse(value["receipt"]["proposal_structure_exact"])

    def test_malformed_or_header_drift_is_identity(self) -> None:
        for candidate in (
            "not a table",
            "| Name | Year | Place |\n| --- | --- | --- |\n| Alpha | 2025 | Paris |",
        ):
            with self.subTest(candidate=candidate):
                value = target.apply_monotone_unknown_fill(
                    baseline=BASELINE, proposed=candidate, pages=[]
                )
                self.assertEqual(value["candidate_table"], BASELINE)
                self.assertFalse(value["receipt"]["proposal_parse_valid"])

    def test_unsupported_or_nonintegral_page_does_not_fill(self) -> None:
        for pages in (
            [page(1, "Alpha record. City: Paris.")],
            [page(1, "Alpha record. Year: 2025.", integrity=False)],
        ):
            with self.subTest(pages=pages):
                value = target.apply_monotone_unknown_fill(
                    baseline=BASELINE,
                    proposed=proposal(alpha_year="2025", beta_city="Unknown"),
                    pages=pages,
                )
                self.assertEqual(value["candidate_table"], BASELINE)
                self.assertEqual(
                    value["receipt"]["rejected_unsupported_fill_count"], 1
                )

    def test_distant_or_substring_evidence_does_not_fill(self) -> None:
        for content in (
            "Alphabet record. Year: 20250.",
            "Alpha record. " + ("unrelated filler " * 40) + "Year: 2025.",
        ):
            with self.subTest(content=content):
                value = target.apply_monotone_unknown_fill(
                    baseline=BASELINE,
                    proposed=proposal(alpha_year="2025", beta_city="Unknown"),
                    pages=[page(1, content)],
                )
                self.assertEqual(value["candidate_table"], BASELINE)

    def test_exact_markdown_row_supports_fill(self) -> None:
        source = """| Name | Year | City |
| --- | --- | --- |
| Alpha | 2025 | Paris |
| Beta | 2024 | Rome |"""
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(),
            pages=[page(1, source)],
        )
        self.assertEqual(value["receipt"]["admitted_unknown_fill_count"], 2)

    def test_bound_conflicting_value_rejects_only_that_fill(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(),
            pages=[
                page(1, "Alpha record. Year: 2025. City: Paris."),
                page(2, "Alpha record. Year: 2026. City: Paris."),
                page(3, "Beta record. Year: 2024. City: Rome."),
            ],
        )
        self.assertIn("| Alpha | Unknown | Paris |", value["candidate_table"])
        self.assertIn("| Beta | 2024 | Rome |", value["candidate_table"])
        receipt = value["receipt"]
        self.assertEqual(receipt["rejected_conflicting_fill_count"], 1)
        self.assertEqual(receipt["admitted_unknown_fill_count"], 1)

    def test_markdown_conflict_rejects_fill(self) -> None:
        source = """| Name | Year | City |
| --- | --- | --- |
| Alpha | 2026 | Paris |"""
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(alpha_year="2025", beta_city="Unknown"),
            pages=[
                page(1, "Alpha record. Year: 2025. City: Paris."),
                page(2, source),
            ],
        )
        self.assertEqual(value["candidate_table"], BASELINE)
        self.assertEqual(
            value["receipt"]["rejected_conflicting_fill_count"], 1
        )

    def test_duplicate_same_value_is_not_a_conflict(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(alpha_year="2025", beta_city="Unknown"),
            pages=[
                page(1, "Alpha record. Year: 2025."),
                page(2, "Alpha record. Year: 2025."),
            ],
        )
        self.assertIn("| Alpha | 2025 | Paris |", value["candidate_table"])
        self.assertEqual(
            value["receipt"]["rejected_conflicting_fill_count"], 0
        )
        self.assertEqual(
            value["receipt"]["supporting_page_count_distribution"], {"2": 1}
        )

    def test_unknown_marker_change_without_fill_is_semantic_identity(self) -> None:
        candidate = table(
            ("Alpha", "N/A", "Paris"),
            ("Beta", "2024", "-"),
        )
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE, proposed=candidate, pages=[]
        )
        self.assertEqual(value["candidate_table"], BASELINE)
        self.assertEqual(value["receipt"]["proposed_unknown_fill_count"], 0)

    def test_receipt_is_content_free_and_label_blind(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(alpha_year="2025", beta_city="Unknown"),
            pages=[page(1, "Alpha record. Year: 2025. City: Paris.")],
        )
        encoded = json.dumps(value["receipt"], sort_keys=True)
        for forbidden in ("Alpha", "2025", "Paris", "https://", "E0001"):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["receipt"]
            [
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_resealed_count_threshold_credit_or_hidden_tamper_fails(self) -> None:
        value = target.apply_monotone_unknown_fill(
            baseline=BASELINE,
            proposed=proposal(alpha_year="2025", beta_city="Unknown"),
            pages=[page(1, "Alpha record. Year: 2025. City: Paris.")],
        )
        for kind in (
            "count",
            "unknown_bound",
            "known_bound",
            "threshold",
            "credit",
            "distribution",
            "integer_key",
            "support_page_bound",
            "parse_counts",
            "hidden",
        ):
            changed = copy.deepcopy(value["receipt"])
            if kind == "count":
                changed["admitted_unknown_fill_count"] = 2
            elif kind == "unknown_bound":
                changed["proposed_unknown_fill_count"] = 3
            elif kind == "known_bound":
                changed["forbidden_known_cell_change_count"] = 4
            elif kind == "threshold":
                changed["minimum_supporting_pages"] = 0
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_used_for_admission_or_credit_sign"
                ] = True
            elif kind == "distribution":
                changed["admitted_supporting_page_count_distribution"] = {
                    "0": 1
                }
            elif kind == "integer_key":
                changed["supporting_page_count_distribution"] = {1: 1}
            elif kind == "support_page_bound":
                changed["supporting_page_count_distribution"] = {"2": 1}
                changed["admitted_supporting_page_count_distribution"] = {
                    "2": 1
                }
                changed["shadow_information_gain_nats"] = round(
                    target._shadow_information_gain(2), 12
                )
            elif kind == "parse_counts":
                changed["proposal_parse_valid"] = False
            else:
                changed["hidden"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_source_has_no_effect_evaluator_or_privileged_routing_capability(self) -> None:
        path = SRC / "deepwide_agent/v25289_monotone_unknown_fill.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "urllib.request",
            "openai",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertEqual(privileged, [])
        for forbidden in ("official_eval", "run_official", "api_key", "os.environ"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
