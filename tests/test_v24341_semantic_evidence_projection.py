from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from deepwide_agent.v24341_semantic_evidence_projection import (  # noqa: E402
    build_semantic_active_catalog,
    validate_semantic_active_catalog,
)


def page(host: str, content: str):
    return {"host": host, "content": content, "fetch_integrity": True}


def values(catalog):
    return {
        item["candidate_value"]
        for item in catalog["active_catalog"]["base_catalog"]["support_sets"]
    }


class V24341SemanticEvidenceProjectionTests(unittest.TestCase):
    def test_founded_and_established_project_to_visible_founding_year(self) -> None:
        target = [CellTarget("Alpha", "Founding year", "Unknown")]
        catalog = build_semantic_active_catalog(
            target,
            [page("one.example", "Alpha was founded in 2025 after a merger.")],
            [page("two.example", "Alpha was established in 2025 by its members.")],
        )
        self.assertIn("2025", values(catalog))
        self.assertEqual(catalog["semantic_projection_count"], 2)
        self.assertEqual(
            catalog["projection_relation_kinds"], {"founding_year": 2}
        )

    def test_headquartered_phrase_projects_city_and_country(self) -> None:
        targets = [
            CellTarget("Alpha", "Headquarters city", "Unknown"),
            CellTarget("Alpha", "Headquarters country", "Unknown"),
        ]
        pages = [
            page(
                "one.example",
                "Alpha is headquartered in London, United Kingdom.",
            ),
            page(
                "two.example",
                "The organization Alpha is based in London, United Kingdom.",
            ),
        ]
        catalog = build_semantic_active_catalog(targets, pages[:1], pages[1:])
        self.assertIn("London", values(catalog))
        self.assertIn("United Kingdom", values(catalog))

    def test_first_flight_and_release_year_aliases_project(self) -> None:
        cases = (
            ("Jet", "First flight year", "Jet made its maiden flight in 2013."),
            ("Tool", "Initial release year", "Tool was first released in 2005."),
        )
        for entity, column, content in cases:
            with self.subTest(column=column):
                targets = [CellTarget(entity, column, "Unknown")]
                catalog = build_semantic_active_catalog(
                    targets,
                    [page("one.example", content)],
                    [page("two.example", content)],
                )
                self.assertEqual(catalog["eligible_support_set_count"], 1)

    def test_unrelated_nearby_year_without_relation_is_not_projected(self) -> None:
        targets = [CellTarget("Alpha", "Founding year", "Unknown")]
        catalog = build_semantic_active_catalog(
            targets,
            [page("one.example", "Alpha won an award in 2025.")],
            [page("two.example", "Alpha published a report in 2025.")],
        )
        self.assertEqual(catalog["semantic_projection_count"], 0)
        self.assertEqual(catalog["eligible_support_set_count"], 0)

    def test_resealed_original_or_projection_tamper_fails_replay(self) -> None:
        targets = [CellTarget("Alpha", "Founding year", "Unknown")]
        catalog = build_semantic_active_catalog(
            targets,
            [page("one.example", "Alpha was founded in 2025.")],
            [page("two.example", "Alpha was established in 2025.")],
        )
        for field in ("original", "projected"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                pages = (
                    altered["original_core_pages"]
                    if field == "original"
                    else altered["projected_core_pages"]
                )
                pages[0]["content"] += " tamper"
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_semantic_active_catalog(altered)


if __name__ == "__main__":
    unittest.main()
