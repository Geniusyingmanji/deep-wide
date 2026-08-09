from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v24980_late_page_bound_projection as old  # noqa: E402
from deepwide_agent import v24984_robust_late_page_projection as target  # noqa: E402


QUESTION = (
    "Return exactly one Markdown table. Column names: Domain, Type, TLD Manager. "
    "Preserve exact spelling. Use values from one public record."
)


def page() -> dict[str, str]:
    return {
        "title": "Public directory",
        "url": "https://example.org/public-directory",
        "text": (
            "navigation boilerplate\n" * 400
            + "Domain | Type | TLD Manager\n"
            + ".aa | country-code | Example Authority\n"
            + ".ab | generic | Other Authority\n"
        ),
    }


class RobustLatePageProjectionTests(unittest.TestCase):
    def test_sentence_style_schema_is_exact_and_content_free(self) -> None:
        schema = target._robust_schema(QUESTION)
        self.assertEqual(
            [column["display"] for column in schema],
            ["Domain", "Type", "TLD Manager"],
        )
        receipt = target._schema_receipt(
            schema, table_count=1, table_record_count=2
        )
        encoded = str(receipt)
        for forbidden in ("Domain", "Type", "TLD Manager", ".aa", "example.org"):
            self.assertNotIn(forbidden, encoded)

    def test_late_full_page_table_restores_all_fields_and_exact_identity(self) -> None:
        legacy = old.build_projection(QUESTION, page())
        candidate = target.build_projection(QUESTION, page())
        receipt = candidate["content_free_receipt"]
        robust = candidate["robust_schema_receipt"]
        # The legacy partial-signature path did engage, but under the greedy
        # last-column label it retained only one field per row.  The robust
        # schema restores both visible target fields without adding a source.
        self.assertTrue(
            legacy["content_free_receipt"]["candidate_evidence_changed"]
        )
        self.assertEqual(
            legacy["content_free_receipt"]["retained_bound_observation_count"],
            2,
        )
        self.assertTrue(receipt["candidate_evidence_changed"])
        self.assertTrue(receipt["mechanism_engaged"])
        self.assertGreaterEqual(receipt["retained_record_count"], 1)
        self.assertEqual(receipt["retained_bound_observation_count"], 4)
        self.assertEqual(robust["full_page_header_bound_table_count"], 1)
        self.assertEqual(robust["full_page_table_record_count"], 2)
        self.assertEqual(len(candidate["projection"]), 5_000)
        self.assertIn(".aa", candidate["projection"])
        self.assertNotEqual(candidate["projection"], page()["text"][:5_000])

    def test_no_schema_or_malformed_table_falls_back_byte_exact(self) -> None:
        raw = page()
        no_schema = target.build_projection("Return a table.", raw)
        malformed = copy.deepcopy(raw)
        malformed["text"] = (
            "navigation boilerplate\n" * 400
            + "Domain | Type | TLD Manager\n"
            + ".aa | missing-value\n"
        )
        bad = target.build_projection(QUESTION, malformed)
        self.assertEqual(no_schema["projection"], raw["text"][:5_000])
        self.assertEqual(bad["projection"], malformed["text"][:5_000])
        self.assertFalse(no_schema["content_free_receipt"]["mechanism_engaged"])
        self.assertFalse(bad["content_free_receipt"]["mechanism_engaged"])

    def test_projection_replay_and_tamper_detection(self) -> None:
        value = target.build_projection(QUESTION, page())
        self.assertEqual(
            target.validate_projection(value, question=QUESTION, page=page()), value
        )
        tampered = copy.deepcopy(value)
        tampered["robust_schema_receipt"][
            "full_page_table_record_count"
        ] += 1
        with self.assertRaises(ValueError):
            target.validate_projection(tampered, question=QUESTION, page=page())


if __name__ == "__main__":
    unittest.main()
