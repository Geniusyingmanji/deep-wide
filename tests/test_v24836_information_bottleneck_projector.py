from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24836_information_bottleneck_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection,
    payload_sha256,
    validate_projection,
)


def page(index: int, text: str, host: str | None = None) -> dict[str, str]:
    return {
        "title": f"Page {index}",
        "url": f"https://{host or f'h{index}.example'}/p{index}",
        "content": text,
    }


class V24836InformationBottleneckProjectorTests(unittest.TestCase):
    def test_each_page_gets_prefix_before_first_page_tail(self) -> None:
        pages = [page(1, "A" * 5_000), page(2, "B" * 5_000), page(3, "C" * 5_000)]
        policy = ProjectionPolicy(
            total_character_cap=3_000,
            minimum_page_prefix_chars=800,
            round_robin_chunk_chars=200,
            maximum_page_chars=5_000,
        )
        result = build_projection(pages, policy=policy)
        self.assertEqual(result["per_page_allocated_characters"], [1000, 1000, 1000])
        self.assertEqual(result["projected_page_count"], 3)

    def test_total_and_per_page_caps_are_hard(self) -> None:
        pages = [page(index, str(index) * 10_000) for index in range(1, 8)]
        result = build_projection(pages)
        self.assertLessEqual(result["allocated_content_characters"], 16_000)
        self.assertTrue(all(value <= 5_000 for value in result["per_page_allocated_characters"]))

    def test_duplicate_url_is_stably_removed(self) -> None:
        pages = [page(1, "first"), {**page(1, "second"), "title": "duplicate"}]
        result = build_projection(pages)
        self.assertEqual(result["input_page_count"], 1)
        self.assertIn("first", result["projection"])
        self.assertNotIn("second", result["projection"])

    def test_host_diversity_is_preserved_when_budget_permits_prefixes(self) -> None:
        pages = [
            page(1, "A" * 900, "one.example"),
            page(2, "B" * 900, "two.example"),
            page(3, "C" * 900, "three.example"),
        ]
        result = build_projection(
            pages,
            policy=ProjectionPolicy(
                total_character_cap=2_400,
                minimum_page_prefix_chars=800,
                round_robin_chunk_chars=800,
                maximum_page_chars=5_000,
            ),
        )
        self.assertEqual(result["projected_unique_host_count"], 3)
        self.assertGreater(result["projected_host_entropy_nats"], 0)

    def test_empty_pages_are_ignored_without_budget_fabrication(self) -> None:
        result = build_projection([page(1, ""), {"title": "bad", "url": "", "content": "x"}])
        self.assertEqual(result["input_page_count"], 0)
        self.assertEqual(result["allocated_content_characters"], 0)
        self.assertIn("No usable web material", result["projection"])

    def test_entropy_is_shadow_only_and_no_privileged_input_exists(self) -> None:
        result = build_projection([page(1, "evidence")])
        self.assertTrue(result["entropy_information_gain_shadow_only"])
        self.assertFalse(result["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(result["question_benchmark_label_mapping_gold_evaluator_score_or_reward_read"])

    def test_replay_and_resealed_tamper_fail_closed(self) -> None:
        pages = [page(1, "A" * 2_000), page(2, "B" * 2_000)]
        result = build_projection(pages)
        self.assertEqual(result, validate_projection(result, pages=pages))
        altered = copy.deepcopy(result)
        altered["per_page_allocated_characters"][0] -= 1
        altered.pop("receipt_sha256")
        altered["receipt_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_projection(altered, pages=pages)

        shortened = copy.deepcopy(result)
        shortened["per_page_content_sha256"].pop()
        shortened.pop("receipt_sha256")
        shortened["receipt_sha256"] = payload_sha256(shortened)
        with self.assertRaises(ValueError):
            validate_projection(shortened, pages=pages)

    def test_bad_policy_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProjectionPolicy(total_character_cap=0).validate()
        with self.assertRaises(ValueError):
            ProjectionPolicy(
                minimum_page_prefix_chars=6_000, maximum_page_chars=5_000
            ).validate()


if __name__ == "__main__":
    unittest.main()
