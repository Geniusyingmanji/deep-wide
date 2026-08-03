from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24333_programmatic_support_catalog import (  # noqa: E402
    CellTarget,
    SupportPage,
    build_support_catalog,
)
from deepwide_agent.v24334_support_catalog_revision_gate import (  # noqa: E402
    apply_catalog_revision,
    payload_sha256,
    validate_revision_result,
)


BASELINE_UNKNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
```"""
BASELINE_KNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | 2024 |
```"""


def proposed(year: str) -> str:
    return f"""```markdown
| Name | Year |
| --- | --- |
| Alpha | {year} |
```"""


def pages(count: int):
    return [
        SupportPage(
            evidence_id=f"R{index:04d}",
            host=f"host{index}.example",
            content="Independent official record. Alpha Year is 2025.",
            fetch_integrity=True,
        )
        for index in range(1, count + 1)
    ]


def declaration(support):
    return [
        {
            "row_key": "Alpha",
            "column": "Year",
            "support_set_id": support["support_set_id"],
            "evidence_ids": support["evidence_ids"],
        }
    ]


class V24334SupportCatalogRevisionGateTests(unittest.TestCase):
    def test_two_host_unknown_fill_changes_candidate_and_receives_credit(self) -> None:
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        result = apply_catalog_revision(
            baseline=BASELINE_UNKNOWN,
            proposed=proposed("2025"),
            cell_support=declaration(support),
            catalog=catalog,
        )
        validate_revision_result(result)
        self.assertIn("| Alpha | 2025 |", result["candidate_table"])
        self.assertFalse(result["candidate_identity_handoff"])
        self.assertEqual(result["admitted_cell_changes"], 1)
        self.assertGreater(result["credited_conditional_entropy_reduction_nats"], 0)

    def test_three_host_known_override_changes_candidate(self) -> None:
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "2024")], pages(3)
        )
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        result = apply_catalog_revision(
            baseline=BASELINE_KNOWN,
            proposed=proposed("2025"),
            cell_support=declaration(support),
            catalog=catalog,
        )
        self.assertIn("| Alpha | 2025 |", result["candidate_table"])
        self.assertEqual(result["admitted_cell_changes"], 1)

    def test_fabricated_or_missing_support_keeps_byte_identical_baseline(self) -> None:
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        result = apply_catalog_revision(
            baseline=BASELINE_UNKNOWN,
            proposed=proposed("2025"),
            cell_support=[
                {
                    "row_key": "Alpha",
                    "column": "Year",
                    "support_set_id": "f" * 64,
                    "evidence_ids": ["R9999"],
                }
            ],
            catalog=catalog,
        )
        self.assertEqual(result["candidate_table"], BASELINE_UNKNOWN)
        self.assertTrue(result["candidate_identity_handoff"])
        self.assertEqual(result["admitted_cell_changes"], 0)

    def test_model_cannot_swap_value_under_valid_support_id(self) -> None:
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        result = apply_catalog_revision(
            baseline=BASELINE_UNKNOWN,
            proposed=proposed("2026"),
            cell_support=declaration(support),
            catalog=catalog,
        )
        self.assertEqual(result["candidate_table"], BASELINE_UNKNOWN)
        self.assertEqual(
            result["cell_resolution_receipts"][0]["disposition"],
            "quarantine_value_binding",
        )

    def test_proposal_cannot_delete_baseline_rows(self) -> None:
        baseline = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
| Beta | 2023 |
```"""
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        result = apply_catalog_revision(
            baseline=baseline,
            proposed=proposed("2025"),
            cell_support=declaration(support),
            catalog=catalog,
        )
        self.assertIn("| Beta | 2023 |", result["candidate_table"])
        self.assertTrue(result["baseline_rows_never_deleted"])

    def test_unsupported_new_row_is_not_added(self) -> None:
        proposed_with_beta = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
| Beta | 2025 |
```"""
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        result = apply_catalog_revision(
            baseline=BASELINE_UNKNOWN,
            proposed=proposed_with_beta,
            cell_support=[],
            catalog=catalog,
        )
        self.assertEqual(result["candidate_table"], BASELINE_UNKNOWN)
        self.assertNotIn("| Beta |", result["candidate_table"])

    def test_resealed_result_credit_tamper_is_rejected(self) -> None:
        catalog = build_support_catalog(
            [CellTarget("Alpha", "Year", "Unknown")], pages(2)
        )
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        result = apply_catalog_revision(
            baseline=BASELINE_UNKNOWN,
            proposed=proposed("2025"),
            cell_support=declaration(support),
            catalog=catalog,
        )
        altered = copy.deepcopy(result)
        altered["credited_conditional_entropy_reduction_nats"] += 1
        altered.pop("result_sha256")
        altered["result_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(ValueError, "revision result drifted"):
            validate_revision_result(altered)


if __name__ == "__main__":
    unittest.main()
