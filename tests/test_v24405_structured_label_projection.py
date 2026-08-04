from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24405_structured_label_projection import (  # noqa: E402
    build_structured_label_projection,
    validate_structured_label_projection,
)


BASELINE = """```markdown
| Software | Initial release year |
| --- | --- |
| OpenRC | Unknown |
| tmux | Unknown |
```"""


def page(host: str, content: str) -> dict:
    return {"host": host, "content": content, "fetch_integrity": True}


def values(catalog: dict, row: str) -> set[str]:
    return {
        str(item["value"])
        for item in catalog["observations"]
        if str(item["row_key"]).casefold() == row.casefold()
    }


class V24405StructuredLabelProjectionTests(unittest.TestCase):
    def test_entity_scoped_infobox_release_is_projected(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "OpenRC\nThe OpenRC logo\nOriginal author | Roy Marples\n"
                    "Release | 5 April 2007; 19 years ago (2007-04-05)\n"
                    "Stable release | 0.63.3 / 2 July 2026\nRepository | example",
                )
            ],
        )
        self.assertEqual(values(catalog, "OpenRC"), {"2007"})
        self.assertEqual(
            catalog["structured_projection_mode_counts"],
            {"entity_block_label_value": 1},
        )
        self.assertEqual(catalog["novel_structured_observation_count"], 1)

    def test_stable_latest_and_release_notes_are_not_initial_release(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "OpenRC\nStable release | 0.63 / 2026\n"
                    "Latest release: 2025\nRelease notes | 2024\nWebsite | example",
                )
            ],
        )
        self.assertEqual(values(catalog, "OpenRC"), set())
        self.assertEqual(catalog["structured_projection_count"], 0)

    def test_cross_target_infobox_values_remain_separate(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "OpenRC\nRelease | 5 April 2007\n\n"
                    "tmux\nInitial release: 20 November 2007\n",
                )
            ],
        )
        self.assertEqual(values(catalog, "OpenRC"), {"2007"})
        self.assertEqual(values(catalog, "tmux"), {"2007"})

    def test_exact_table_header_binds_entity_row(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "Software | Initial release year | Language\n"
                    "--- | --- | ---\nOpenRC | 2007 | C\ntmux | 2007 | C",
                )
            ],
        )
        self.assertEqual(values(catalog, "OpenRC"), {"2007"})
        self.assertEqual(values(catalog, "tmux"), {"2007"})
        self.assertEqual(
            catalog["structured_projection_mode_counts"],
            {"table_header_value": 2},
        )

    def test_unlabelled_nearby_year_and_unheaded_row_are_rejected(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "OpenRC\nThe project won an award in 2007\n\n"
                    "OpenRC | 2007\ntmux | 2008",
                )
            ],
        )
        self.assertEqual(catalog["observations"], [])
        self.assertFalse(catalog["arbitrary_nearby_year_used_as_observation"])

    def test_legacy_prose_observation_is_preserved_and_deduplicated(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [page("one.example", "OpenRC was initially released in 2007.")],
        )
        self.assertEqual(values(catalog, "OpenRC"), {"2007"})
        self.assertEqual(catalog["legacy_observation_count"], 1)
        self.assertEqual(catalog["structured_projection_count"], 0)
        self.assertEqual(catalog["combined_observation_count"], 1)

    def test_selected_identity_limits_projection(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [
                page(
                    "one.example",
                    "OpenRC\nRelease | 2007\n\ntmux\nRelease | 2008",
                )
            ],
            selected_identities={("openrc", "initialreleaseyear")},
        )
        self.assertEqual(values(catalog, "OpenRC"), {"2007"})
        self.assertEqual(values(catalog, "tmux"), set())

    def test_catalog_tamper_fails_closed_and_policy_is_label_blind(self) -> None:
        catalog = build_structured_label_projection(
            BASELINE,
            [page("one.example", "OpenRC\nRelease | 2007")],
        )
        self.assertFalse(
            catalog[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(catalog["benchmark_launch_or_evaluator_authorized"])
        for field in ("page", "projection", "claim"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                if field == "page":
                    altered["pages"][0]["content"] = altered["pages"][0][
                        "content"
                    ].replace("2007", "2008")
                elif field == "projection":
                    altered["structured_projections"][0]["value"] = "2008"
                else:
                    altered["arbitrary_nearby_year_used_as_observation"] = True
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_structured_label_projection(altered)


if __name__ == "__main__":
    unittest.main()
