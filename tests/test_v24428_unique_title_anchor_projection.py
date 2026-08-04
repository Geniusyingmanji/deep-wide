from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24428_unique_title_anchor_projection import (  # noqa: E402
    build_unique_title_anchor_projection,
    validate_unique_title_anchor_projection,
)


BASELINE = """```markdown
| Football club | Founding year |
| --- | --- |
| Arsenal | Unknown |
| Chelsea | Unknown |
| Atlético Madrid | Unknown |
| AC Milan | Unknown |
```"""


def page(title: str, content: str, host: str = "one.example") -> dict:
    return {
        "host": host,
        "title": title,
        "content": content,
        "fetch_integrity": True,
    }


def values(catalog: dict, row: str) -> set[str]:
    return {
        str(item["value"])
        for item in catalog["observations"]
        if str(item["row_key"]).casefold() == row.casefold()
    }


class V24428UniqueTitleAnchorProjectionTests(unittest.TestCase):
    def test_unique_complete_title_surface_binds_exact_labelled_year(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Arsenal F.C. - Wikipedia", "Full name | Arsenal Football Club\nFounded | October 1886\nGround | Emirates")],
        )
        self.assertEqual(values(catalog, "Arsenal"), {"1886"})
        self.assertEqual(catalog["parent_observation_count"], 0)
        self.assertEqual(catalog["unique_title_anchor_page_count"], 1)
        self.assertEqual(catalog["novel_title_anchor_observation_count"], 1)
        self.assertEqual(
            catalog["title_anchor_projection_mode_counts"],
            {"unique_title_anchor_label_value": 1},
        )

    def test_acronym_punctuation_and_accent_folding_are_deterministic(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [
                page("A.C. Milan | Official site", "Founded: 1899", "milan.example"),
                page("Atletico Madrid - History", "Founding year | 1903", "atleti.example"),
            ],
        )
        self.assertEqual(values(catalog, "AC Milan"), {"1899"})
        self.assertEqual(values(catalog, "Atlético Madrid"), {"1903"})

    def test_label_without_unique_title_anchor_is_rejected(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Premier League clubs", "Founded | 1886")],
        )
        self.assertEqual(catalog["observations"], [])
        self.assertEqual(catalog["unique_title_anchor_page_count"], 0)
        self.assertFalse(catalog["arbitrary_nearby_year_used_as_observation"])

    def test_title_matching_two_visible_rows_is_rejected(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Arsenal vs Chelsea - history", "Founded | 1886")],
        )
        self.assertEqual(catalog["observations"], [])
        self.assertEqual(catalog["ambiguous_or_absent_title_anchor_page_count"], 1)

    def test_conflicting_labelled_years_reject_the_page_target_pair(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Chelsea F.C. - Wikipedia", "Founded | 1904\nEstablishment year | 1905")],
        )
        self.assertEqual(values(catalog, "Chelsea"), set())
        self.assertEqual(catalog["title_anchor_projection_count"], 0)

    def test_unlabelled_nearby_year_and_unaccepted_label_are_rejected(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Arsenal F.C.", "Won a cup in 1886\nLatest season | 2026")],
        )
        self.assertEqual(catalog["observations"], [])

    def test_selected_identity_limits_title_projection(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Arsenal F.C.", "Founded | 1886")],
            selected_identities={("chelsea", "foundingyear")},
        )
        self.assertEqual(catalog["observations"], [])
        self.assertEqual(catalog["title_anchor_projection_count"], 0)

    def test_parent_projection_is_preserved_and_replay_tamper_fails(self) -> None:
        catalog = build_unique_title_anchor_projection(
            BASELINE,
            [page("Unrelated page", "Chelsea\nFounded | 1905")],
        )
        self.assertEqual(values(catalog, "Chelsea"), {"1905"})
        self.assertEqual(catalog["parent_observation_count"], 1)
        self.assertEqual(catalog["novel_title_anchor_observation_count"], 0)
        self.assertFalse(
            catalog[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(catalog["benchmark_launch_or_evaluator_authorized"])
        for field in ("title", "projection", "claim"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                if field == "title":
                    altered["pages"][0]["title"] = "Chelsea F.C."
                elif field == "projection":
                    altered["parent_projection"]["observations"][0]["value"] = "1904"
                else:
                    altered["single_distinct_labelled_year_required"] = False
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_unique_title_anchor_projection(altered)


if __name__ == "__main__":
    unittest.main()
