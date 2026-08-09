from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24980_late_page_bound_projection as target  # noqa: E402


QUESTION = (
    "Use the supplied public page and return one Markdown table.\n"
    "Column names: Entity | Target value | Observation date\n"
    "<ENTITIES>Late Entity [LTE]</ENTITIES>"
)


def page(content: str) -> dict[str, str]:
    return {
        "title": "Official records",
        "url": "https://official.example/public/records",
        "text": content,
    }


class V24980LatePageBoundProjectionTests(unittest.TestCase):
    def test_recovers_identity_target_bound_record_after_parent_prefix(self) -> None:
        content = (
            ("Public archive boilerplate without requested records.\n" * 160)
            + "\n| Entity | Target value | Observation date |\n"
            + "|---|---|---|\n"
            + "| Early Entity | 17 | 2025-01-01 |\n"
            + "| Late Entity [LTE] | 999 | 2025-02-03 |\n"
        )
        self.assertNotIn("Late Entity [LTE]", content[: target.PAGE_CHARACTER_CAP])
        value = target.build_projection(QUESTION, page(content))
        receipt = value["content_free_receipt"]
        self.assertLessEqual(len(value["projection"]), target.PAGE_CHARACTER_CAP)
        self.assertEqual(len(value["projection"]), len(content[: target.PAGE_CHARACTER_CAP]))
        self.assertIn("Late Entity [LTE]", value["projection"])
        self.assertIn("999", value["projection"])
        self.assertIn("source_url=https://official.example/public/records", value["projection"])
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertFalse(receipt["exact_parent_prefix_handoff"])
        self.assertGreaterEqual(receipt["retained_bound_observation_count"], 2)

    def test_no_safe_schema_binding_is_exact_parent_prefix_handoff(self) -> None:
        content = "unstructured public narrative " * 400
        value = target.build_projection(
            "Summarize the supplied page without a table schema.", page(content)
        )
        self.assertEqual(value["projection"], content[: target.PAGE_CHARACTER_CAP])
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["exact_parent_prefix_handoff"])
        self.assertFalse(receipt["mechanism_engaged"])
        self.assertEqual(receipt["retained_record_count"], 0)

    def test_conflicting_coordinate_is_omitted_and_hands_off(self) -> None:
        content = (
            "| Entity | Target value | Observation date |\n"
            "|---|---|---|\n"
            "| Late Entity [LTE] | 999 | 2025-02-03 |\n\n"
            "| Entity | Target value | Observation date |\n"
            "|---|---|---|\n"
            "| Late Entity [LTE] | 111 | 2025-02-03 |\n"
        ) + ("padding " * 900)
        value = target.build_projection(QUESTION, page(content))
        receipt = value["content_free_receipt"]
        self.assertGreaterEqual(receipt["conflicting_coordinate_count"], 1)
        projection = value["projection"]
        if receipt["mechanism_engaged"]:
            compact = projection.split("[INHERITED RAW PAGE PREFIX]", 1)[0]
            self.assertNotIn('"Target value","999"', compact)
            self.assertNotIn('"Target value","111"', compact)

    def test_visible_entity_is_ranked_before_large_earlier_table_tail(self) -> None:
        rows = "".join(
            f"| Entity {index:03d} | {index} | 2024-01-01 |\n"
            for index in range(90)
        )
        content = (
            "archive\n" * 700
            + "| Entity | Target value | Observation date |\n"
            + "|---|---|---|\n"
            + rows
            + "| Late Entity [LTE] | 999 | 2025-02-03 |\n"
        )
        value = target.build_projection(QUESTION, page(content))
        self.assertIn("Late Entity [LTE]", value["projection"])
        self.assertTrue(value["content_free_receipt"]["mechanism_engaged"])

    def test_compact_records_are_not_cut_at_parent_cap(self) -> None:
        rows = "".join(
            f"| Entity {index:03d} | value-{index:03d} | 2024-01-01 |\n"
            for index in range(100)
        )
        content = (
            "| Entity | Target value | Observation date |\n"
            "|---|---|---|\n" + rows
        )
        value = target.build_projection(QUESTION, page(content))
        projection = value["projection"]
        self.assertLessEqual(len(projection), target.PAGE_CHARACTER_CAP)
        if value["content_free_receipt"]["mechanism_engaged"]:
            compact = projection.split("\n[INHERITED RAW PAGE PREFIX]\n", 1)[0]
            self.assertTrue(compact.endswith("[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]"))
            for line in compact.splitlines()[5:-1]:
                self.assertTrue(line.startswith('{"record_id":'))
                self.assertTrue(line.endswith("}"))

    def test_ambiguous_header_fails_closed_to_prefix(self) -> None:
        content = (
            "| Entity | Target value | Target value |\n"
            "|---|---|---|\n"
            "| Late Entity [LTE] | 999 | 111 |\n"
        ) + ("padding " * 900)
        value = target.build_projection(QUESTION, page(content))
        self.assertEqual(value["projection"], content[: target.PAGE_CHARACTER_CAP])
        self.assertTrue(value["content_free_receipt"]["exact_parent_prefix_handoff"])

    def test_receipt_tamper_is_rejected(self) -> None:
        content = (
            "| Entity | Target value | Observation date |\n"
            "|---|---|---|\n"
            "| Late Entity [LTE] | 999 | 2025-02-03 |\n"
        )
        value = target.build_projection(QUESTION, page(content))
        receipt = copy.deepcopy(value["content_free_receipt"])
        receipt["positive_signed_credit_count"] = 1
        with self.assertRaises(ValueError):
            target.validate_receipt(receipt)

    def test_oversized_or_nul_page_is_rejected_before_projection(self) -> None:
        with self.assertRaises(ValueError):
            target.build_projection(QUESTION, page("safe\x00unsafe"))
        with self.assertRaises(ValueError):
            target.build_projection(
                QUESTION,
                page("x" * (target.MAXIMUM_INPUT_PAGE_CHARACTERS + 1)),
            )


if __name__ == "__main__":
    unittest.main()
