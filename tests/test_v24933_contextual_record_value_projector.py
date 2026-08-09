from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24921_target_value_coverage_projector as parent  # noqa: E402
from deepwide_agent import v24933_contextual_record_value_projector as candidate  # noqa: E402


QUESTION = """Return exactly one Markdown table. Column names: Entity | Population [POP] @2024.
<ENTITIES>
1. Alpha [ALP]
2. Beta [BET]
</ENTITIES>"""


def narrative_pages() -> list[dict[str, str]]:
    filler = "\n\n".join(
        f"Background section {index}. General material without requested entities."
        for index in range(28)
    )
    return [
        {
            "title": "Official population report",
            "url": "https://example.test/report",
            "content": (
                "# Population [POP] @2024\n\n"
                "Alpha [ALP]: 991\nBeta [BET]: 881\n\n"
                + filler
            ),
        }
    ]


class V24933ContextualRecordValueProjectorTests(unittest.TestCase):
    def test_narrative_heading_context_creates_bound_pairs(self) -> None:
        value = candidate.build_projection(QUESTION, narrative_pages())
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["supported_contextual_target_value_pair_count"], 2)
        self.assertEqual(receipt["retained_contextual_target_value_pair_count"], 2)
        self.assertGreaterEqual(receipt["context_dependency_addition_count"], 1)
        self.assertIn("Alpha [ALP]: 991", value["projection"])
        self.assertIn("Population [POP] @2024", value["projection"])

    def test_parent_has_no_joint_pair_for_heading_followed_by_records(self) -> None:
        value = parent.build_projection(QUESTION, narrative_pages())
        self.assertEqual(
            value["content_free_receipt"]["supported_target_value_pair_count"], 0
        )

    def test_value_token_is_required_for_contextual_pair(self) -> None:
        pages = narrative_pages()
        pages[0]["content"] = "# Population [POP] @2024\n\nAlpha [ALP]: Unknown"
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(
            value["content_free_receipt"][
                "supported_contextual_target_value_pair_count"
            ],
            0,
        )

    def test_new_section_clears_target_context(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://example.test/report",
                "content": (
                    "# Population [POP] @2024\n\nAlpha [ALP]: 991\n\n"
                    "# Unrelated notes\n\nBeta [BET]: 881"
                ),
            }
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(
            value["content_free_receipt"][
                "supported_contextual_target_value_pair_count"
            ],
            1,
        )

    def test_local_row_target_value_pair_does_not_need_context_dependency(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://example.test/record",
                "content": "Alpha [ALP] Population [POP] @2024: 991",
            }
        ]
        value = candidate.build_projection(QUESTION, pages)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["supported_bound_target_value_pair_count"], 1)
        self.assertEqual(receipt["supported_contextual_target_value_pair_count"], 0)
        self.assertEqual(receipt["context_dependency_addition_count"], 0)

    def test_unicode_expansion_remains_total(self) -> None:
        pages = narrative_pages()
        pages[0]["content"] += "\nCompatibility: ½ ℃ ™"
        value = candidate.build_projection(QUESTION, pages)
        receipt = value["unicode_total_compaction_receipt"]
        self.assertGreater(receipt["nfkc_expansion_characters"], 0)
        self.assertEqual(receipt["compaction_budget_domain"], "nfkc_normalized_input_characters")

    def test_caps_and_source_order_are_preserved(self) -> None:
        pages = narrative_pages() + [
            {
                "title": "Second source",
                "url": "https://second.example/report",
                "content": "# Population [POP] @2024\n\nAlpha [ALP]: 992",
            }
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertLessEqual(value["projected_rendered_characters"], 30_000)
        self.assertTrue(all(number <= 5_000 for number in value["per_page_allocated_characters"]))
        self.assertEqual(value["projected_page_count"], 2)
        self.assertLess(
            value["projection"].index("example.test/report"),
            value["projection"].index("second.example/report"),
        )

    def test_replay_and_tamper_detection(self) -> None:
        value = candidate.build_projection(QUESTION, narrative_pages())
        self.assertEqual(
            candidate.validate_projection(
                value, question=QUESTION, pages=narrative_pages()
            ),
            value,
        )
        tampered = copy.deepcopy(value)
        tampered["content_free_receipt"][
            "retained_contextual_target_value_pair_count"
        ] += 1
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered, question=QUESTION, pages=narrative_pages(), replay=False
            )

    def test_runtime_module_has_no_io_network_model_or_process_capability(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v24933_contextual_record_value_projector.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue(
            imports.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "socket",
                    "subprocess",
                    "requests",
                    "httpx",
                    "openai",
                    "importlib",
                    "runpy",
                }
            )
        )
        self.assertNotIn("ground_truth", source)
        self.assertNotIn("question_type", source)
        self.assertNotIn("answer_key", source)

    def test_entropy_and_information_gain_never_assign_credit(self) -> None:
        value = candidate.build_projection(QUESTION, narrative_pages())
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["entropy_information_gain_shadow_only"])
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])


if __name__ == "__main__":
    unittest.main()
