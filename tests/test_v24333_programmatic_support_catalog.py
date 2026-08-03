from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import (  # noqa: E402
    CellTarget,
    SupportPage,
    build_support_catalog,
    resolve_support_selection,
    validate_catalog_identity,
    validate_resolution_receipt,
    validate_support_catalog,
)


def page(index: int, host: str, year: str = "2025", *, integrity: bool = True):
    return SupportPage(
        evidence_id=f"R{index:04d}",
        host=host,
        content=f"Independent publication. Alpha year is {year}. End of record.",
        fetch_integrity=integrity,
    )


class V24333ProgrammaticSupportCatalogTests(unittest.TestCase):
    def test_two_independent_hosts_naturally_build_unknown_fill_before_revision(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        validate_support_catalog(catalog, targets, pages)
        matches = [
            item
            for item in catalog["support_sets"]
            if item["candidate_value"] == "2025"
        ]
        self.assertEqual(len(matches), 1)
        support = matches[0]
        self.assertEqual(support["independent_source_count"], 2)
        receipt = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["disposition"], "admit_programmatic_support")
        self.assertGreater(receipt["conditional_entropy_reduction_nats"], 0)

    def test_three_independent_hosts_naturally_build_known_override(self) -> None:
        targets = [CellTarget("Alpha", "Year", "2024")]
        pages = [
            page(1, "one.example"),
            page(2, "two.example"),
            page(3, "three.example"),
        ]
        catalog = build_support_catalog(targets, pages)
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        self.assertEqual(support["required_source_count"], 3)
        receipt = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["disposition"], "admit_programmatic_override")

    def test_same_registrable_domain_subdomains_are_not_independent(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "a.example.org"), page(2, "b.example.org")]
        catalog = build_support_catalog(targets, pages)
        self.assertFalse(
            any(item["candidate_value"] == "2025" for item in catalog["support_sets"])
        )
        self.assertGreater(
            catalog["quarantined_candidate_groups"].get(
                "quarantine_insufficient_independence", 0
            ),
            0,
        )

    def test_bad_fetch_does_not_create_support(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example", integrity=False)]
        catalog = build_support_catalog(targets, pages)
        self.assertFalse(
            any(item["candidate_value"] == "2025" for item in catalog["support_sets"])
        )
        self.assertEqual(catalog["intact_page_count"], 1)

    def test_fabricated_support_id_and_citations_remain_quarantined(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        unknown = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id="f" * 64,
            declared_evidence_ids=["R9999"],
        )
        self.assertFalse(unknown["admitted"])
        self.assertEqual(unknown["disposition"], "quarantine_unknown_support_set")
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        bad_citation = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=["R9999"],
        )
        self.assertFalse(bad_citation["admitted"])
        self.assertEqual(
            bad_citation["disposition"], "quarantine_evidence_binding"
        )

    def test_reordered_valid_evidence_ids_are_still_binding_tamper(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        receipt = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=list(reversed(support["evidence_ids"])),
        )
        self.assertFalse(receipt["admitted"])
        self.assertEqual(receipt["disposition"], "quarantine_evidence_binding")

    def test_value_and_target_mismatch_remain_quarantined(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        for overrides, expected in (
            ({"row_key": "Beta"}, "quarantine_target_binding"),
            ({"new_value": "2026"}, "quarantine_value_binding"),
        ):
            with self.subTest(expected=expected):
                inputs = {
                    "row_key": "Alpha",
                    "column": "Year",
                    "new_value": "2025",
                    "support_set_id": support["support_set_id"],
                    "declared_evidence_ids": support["evidence_ids"],
                    **overrides,
                }
                receipt = resolve_support_selection(catalog, **inputs)
                self.assertFalse(receipt["admitted"])
                self.assertEqual(receipt["disposition"], expected)

    def test_public_resolution_receipt_is_content_free(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        support = next(
            item for item in catalog["support_sets"] if item["candidate_value"] == "2025"
        )
        receipt = resolve_support_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        validate_resolution_receipt(receipt)
        encoded = json.dumps(receipt)
        for forbidden in ("Alpha", "2025", "R0001", "one.example"):
            self.assertNotIn(forbidden, encoded)

    def test_resealed_catalog_tamper_fails_replay(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        pages = [page(1, "one.example"), page(2, "two.example")]
        catalog = build_support_catalog(targets, pages)
        altered = copy.deepcopy(catalog)
        altered["support_sets"][0]["candidate_value"] = "2026"
        altered["support_sets"][0]["candidate_value_sha256"] = __import__(
            "hashlib"
        ).sha256(b"2026").hexdigest()
        altered.pop("catalog_payload_sha256")
        altered["catalog_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_catalog_identity(altered)


if __name__ == "__main__":
    unittest.main()
