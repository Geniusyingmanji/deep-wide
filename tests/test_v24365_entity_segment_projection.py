from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    _normalize,
    build_target_segment_catalog,
    validate_target_segment_catalog,
)


def page(host: str, content: str) -> dict:
    return {"host": host, "content": content, "fetch_integrity": True}


def digest(value: str) -> str:
    return hashlib.sha256(_normalize(value).encode("utf-8")).hexdigest()


def projected_values(catalog: dict, target: CellTarget) -> set[str]:
    return {
        item["normalized_value_sha256"]
        for item in catalog["projections"]
        if item["target_binding_sha256"] == target.binding_sha256
    }


class V24365EntitySegmentProjectionTests(unittest.TestCase):
    def test_adjacent_target_relation_is_not_bound_as_conflict(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        beta = CellTarget("Beta", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha, beta],
            [
                page(
                    "one.example",
                    "Alpha was founded in 2025, while Beta was founded in 2024.",
                )
            ],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), {digest("2025")})
        self.assertEqual(projected_values(catalog, beta), {digest("2024")})
        self.assertNotIn(digest("2024"), projected_values(catalog, alpha))

    def test_sentence_boundary_blocks_unlisted_entity_relation(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha],
            [
                page(
                    "one.example",
                    "Alpha was founded in 2025. An unrelated organization was founded in 2024.",
                )
            ],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), {digest("2025")})

    def test_nearest_forward_relation_wins_inside_target_segment(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha],
            [
                page(
                    "one.example",
                    "Alpha was founded in 2025, after a predecessor was established in 2024",
                )
            ],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), {digest("2025")})

    def test_forward_relation_precedes_nearby_leading_relation(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha],
            [page("one.example", "Founded in 1999, Alpha was founded in 2025")],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), {digest("2025")})
        self.assertEqual(catalog["projection_binding_directions"], {"forward": 1})

    def test_tight_leading_relation_is_supported_as_fallback(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha],
            [page("one.example", "Founded in 2025, Alpha remains active")],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), {digest("2025")})
        self.assertEqual(catalog["projection_binding_directions"], {"leading": 1})

    def test_entity_word_boundary_rejects_substring_match(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [alpha],
            [page("one.example", "AlphaWorks was founded in 2025.")],
            [],
        )
        self.assertEqual(projected_values(catalog, alpha), set())

    def test_new_visible_column_relations_form_support_sets(self) -> None:
        cases = (
            ("Language", "First appeared year", "first appeared in", "2009"),
            ("Museum", "Opening year", "opened in", "1793"),
            ("Festival", "First held year", "was first held in", "1970"),
            ("Building", "Architectural height metres", "architectural height is", "828"),
        )
        for entity, column, relation, value in cases:
            with self.subTest(column=column):
                target = CellTarget(entity, column, "Unknown")
                content = f"{entity} {relation} {value}."
                catalog = build_target_segment_catalog(
                    [target],
                    [page("one.example", content)],
                    [page("two.example", content)],
                )
                self.assertEqual(projected_values(catalog, target), {digest(value)})
                self.assertEqual(catalog["eligible_support_set_count"], 1)

    def test_original_projection_and_binding_tamper_fail_replay(self) -> None:
        target = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [target],
            [page("one.example", "Alpha was founded in 2025.")],
            [page("two.example", "Alpha was established in 2025.")],
        )
        for field in ("original", "projection", "binding"):
            with self.subTest(field=field):
                altered = copy.deepcopy(catalog)
                if field == "original":
                    altered["original_core_pages"][0]["content"] += " tamper"
                elif field == "projection":
                    altered["projections"][0]["normalized_value_sha256"] = "f" * 64
                else:
                    altered["cross_target_relation_allowed"] = True
                altered.pop("catalog_payload_sha256")
                altered["catalog_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_target_segment_catalog(altered)

    def test_public_receipt_flags_remain_label_blind(self) -> None:
        target = CellTarget("Alpha", "Founding year", "Unknown")
        catalog = build_target_segment_catalog(
            [target],
            [page("one.example", "Alpha was founded in 2025.")],
            [],
        )
        self.assertFalse(
            catalog[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(catalog["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
