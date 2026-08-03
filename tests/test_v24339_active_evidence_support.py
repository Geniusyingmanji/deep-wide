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
from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from deepwide_agent.v24339_active_evidence_support import (  # noqa: E402
    build_active_catalog,
    resolve_active_selection,
    validate_active_catalog,
    validate_active_resolution,
)


def page(host: str, content: str):
    return {"host": host, "content": content, "fetch_integrity": True}


class V24339ActiveEvidenceSupportTests(unittest.TestCase):
    def test_mixed_core_reserve_two_host_unknown_support_is_eligible(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        catalog = build_active_catalog(
            targets,
            [page("core.example", "Alpha Year is 2025.")],
            [page("reserve.example", "Independent record: Alpha Year is 2025.")],
        )
        validate_active_catalog(catalog, targets=targets)
        support = next(
            item
            for item in catalog["base_catalog"]["support_sets"]
            if item["candidate_value"] == "2025"
        )
        receipt = resolve_active_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        validate_active_resolution(receipt)
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["support_scope"], "mixed")
        self.assertEqual(receipt["core_evidence_count"], 1)
        self.assertEqual(receipt["reserve_evidence_count"], 1)
        self.assertGreater(receipt["conditional_entropy_reduction_nats"], 0)

    def test_two_core_hosts_can_recover_a_missed_baseline_fact(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        catalog = build_active_catalog(
            targets,
            [
                page("one.example", "Alpha Year is 2025."),
                page("two.example", "Alpha Year is 2025."),
            ],
            [],
        )
        support = next(
            item
            for item in catalog["base_catalog"]["support_sets"]
            if item["candidate_value"] == "2025"
        )
        receipt = resolve_active_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value="2025",
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["support_scope"], "core")

    def test_same_host_across_core_and_reserve_is_not_independent(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        catalog = build_active_catalog(
            targets,
            [page("a.example.org", "Alpha Year is 2025.")],
            [page("b.example.org", "Alpha Year is 2025.")],
        )
        self.assertFalse(
            any(
                item["candidate_value"] == "2025"
                for item in catalog["base_catalog"]["support_sets"]
            )
        )

    def test_public_resolution_is_content_free_and_discloses_nonreserve_ablation(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        catalog = build_active_catalog(
            targets,
            [page("core.example", "Alpha Year is 2025.")],
            [page("reserve.example", "Alpha Year is 2025.")],
        )
        self.assertFalse(catalog["pure_reserve_effect_ablation"])
        support = catalog["base_catalog"]["support_sets"][0]
        receipt = resolve_active_selection(
            catalog,
            row_key="Alpha",
            column="Year",
            new_value=support["candidate_value"],
            support_set_id=support["support_set_id"],
            declared_evidence_ids=support["evidence_ids"],
        )
        encoded = json.dumps(receipt)
        for forbidden in ("Alpha", "2025", "core.example", "R0001"):
            self.assertNotIn(forbidden, encoded)

    def test_resealed_scope_or_page_tamper_fails_replay(self) -> None:
        targets = [CellTarget("Alpha", "Year", "Unknown")]
        catalog = build_active_catalog(
            targets,
            [page("core.example", "Alpha Year is 2025.")],
            [page("reserve.example", "Alpha Year is 2025.")],
        )
        for field in ("scope", "page"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                if field == "scope":
                    altered["active_scope_by_evidence_id"]["R0001"] = "reserve"
                else:
                    altered["active_pages"][0]["content"] = "Alpha Year is 2026."
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_active_catalog(altered, targets=targets)


if __name__ == "__main__":
    unittest.main()
