from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    _target_identity,
)
from deepwide_agent.v24436_narrative_title_anchor_projection import (  # noqa: E402
    REASONS,
    build_narrative_title_anchor_projection,
    validate_narrative_title_anchor_projection,
)


BASELINE = """```markdown
| Team | Founding year |
| --- | --- |
| Arizona Cardinals | Unknown |
| Atlanta Falcons | Unknown |
| Baltimore Ravens | Unknown |
| Buffalo Bills | Unknown |
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


class V24436NarrativeTitleAnchorProjectionTests(unittest.TestCase):
    def test_unique_title_accepts_explicit_narrative_relation(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page(
                    "Arizona Cardinals - official history",
                    "The club was founded in 1898 and later moved cities.",
                )
            ],
        )
        self.assertEqual(values(catalog, "Arizona Cardinals"), {"1898"})
        self.assertEqual(catalog["parent_title_anchor_projection_count"], 0)
        self.assertEqual(catalog["narrative_projection_count"], 1)
        self.assertEqual(catalog["novel_narrative_observation_count"], 1)
        self.assertEqual(
            catalog["reason_counts"]["narrative_projection_emitted"], 1
        )
        self.assertTrue(catalog["reason_partition_exact"])

    def test_established_or_formed_relation_is_accepted(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page(
                    "Atlanta Falcons | encyclopedia",
                    "The franchise was established in 1965.",
                    "atlanta.example",
                ),
                page(
                    "Baltimore Ravens history",
                    "The team formed in 1996.",
                    "baltimore.example",
                ),
            ],
        )
        self.assertEqual(values(catalog, "Atlanta Falcons"), {"1965"})
        self.assertEqual(values(catalog, "Baltimore Ravens"), {"1996"})

    def test_nearby_year_without_relation_is_rejected(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [page("Buffalo Bills", "The 1960 season began with eight teams.")],
        )
        self.assertEqual(values(catalog, "Buffalo Bills"), set())
        self.assertEqual(
            catalog["reason_counts"]["explicit_narrative_relation_absent"], 1
        )
        self.assertFalse(catalog["arbitrary_nearby_year_used_as_observation"])

    def test_conflicting_explicit_years_reject_page_target_pair(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page(
                    "Arizona Cardinals",
                    "The club was founded in 1898.\nThe franchise was established in 1920.",
                )
            ],
        )
        self.assertEqual(values(catalog, "Arizona Cardinals"), set())
        self.assertEqual(
            catalog["reason_counts"]["multiple_distinct_narrative_years"], 1
        )

    def test_other_visible_row_stops_title_scope(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page(
                    "Arizona Cardinals",
                    "Atlanta Falcons were established in 1965.\nThe club was founded in 1898.",
                )
            ],
        )
        self.assertEqual(values(catalog, "Arizona Cardinals"), set())
        self.assertEqual(
            catalog["reason_counts"]["explicit_narrative_relation_absent"], 1
        )

    def test_title_anchor_must_match_selected_target_row(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [page("Atlanta Falcons", "The franchise was established in 1965.")],
            selected_identities={
                _target_identity("Arizona Cardinals", "Founding year")
            },
        )
        self.assertEqual(catalog["narrative_projection_count"], 0)
        self.assertEqual(
            catalog["reason_counts"]["title_anchor_other_selected_row"], 1
        )

    def test_reason_partition_is_exact_for_all_page_target_pairs(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page("Unrelated sports page", "Founded in 1900."),
                page("Arizona Cardinals", "Founded in 1898."),
            ],
        )
        self.assertEqual(catalog["page_target_pair_count"], 8)
        self.assertEqual(
            sum(catalog["reason_counts"][name] for name in REASONS), 8
        )

    def test_parent_key_value_observation_is_preserved_and_deduplicated(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [
                page(
                    "Arizona Cardinals",
                    "Founded | 1898\nThe club was founded in 1898.",
                )
            ],
        )
        self.assertEqual(catalog["parent_title_anchor_projection_count"], 1)
        self.assertEqual(catalog["narrative_projection_count"], 1)
        self.assertEqual(catalog["novel_narrative_observation_count"], 0)
        self.assertEqual(values(catalog, "Arizona Cardinals"), {"1898"})

    def test_projection_or_claim_tamper_fails_replay(self) -> None:
        catalog = build_narrative_title_anchor_projection(
            BASELINE,
            [page("Arizona Cardinals", "The club was founded in 1898.")],
        )
        for field in ("projection", "reason", "claim"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                if field == "projection":
                    altered["narrative_title_projections"][0]["value"] = "1900"
                elif field == "reason":
                    altered["reason_counts"]["narrative_projection_emitted"] += 1
                else:
                    altered["arbitrary_nearby_year_used_as_observation"] = True
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_narrative_title_anchor_projection(altered)


if __name__ == "__main__":
    unittest.main()
