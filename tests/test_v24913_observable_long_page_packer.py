from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24911_long_page_evidence_packer import (  # noqa: E402
    PackingPolicy,
    payload_sha256,
)
from deepwide_agent.v24913_observable_long_page_packer import (  # noqa: E402
    build_observable_packing,
    validate_receipt,
)


QUESTION = (
    "Return one table with columns: Country | Target Metric.\n"
    "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
)


def page(content: str) -> dict[str, str]:
    return {
        "title": "Official data",
        "url": "https://official.example/data",
        "content": content,
    }


class V24913ObservableLongPagePackerTests(unittest.TestCase):
    def test_short_page_receipt_is_content_free_and_identity(self) -> None:
        result = build_observable_packing(
            QUESTION, [page("Omega Republic [OMG]: 999")]
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["short_page_identity_count"], 1)
        self.assertEqual(receipt["long_page_packed_count"], 0)
        self.assertFalse(receipt["long_page_mechanism_engaged"])
        encoded = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("Omega Republic", encoded)
        self.assertNotIn("official.example", encoded)
        self.assertNotIn("projection_sha256", encoded)

    def test_long_page_mechanism_engagement_is_observable(self) -> None:
        content = "boilerplate " * 600 + "\nOmega Republic [OMG]: 999"
        result = build_observable_packing(QUESTION, [page(content)])
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["long_page_packed_count"], 1)
        self.assertGreater(receipt["input_characters_beyond_output_page_cap"], 0)
        self.assertTrue(receipt["projection_differs_from_prefix_baseline"])
        self.assertTrue(receipt["long_page_mechanism_engaged"])
        self.assertGreaterEqual(receipt["candidate_visible_requirement_gain_count"], 1)

    def test_prefix_safe_fallback_is_counted_without_content(self) -> None:
        content = "Omega Republic [OMG] prefix\n" + "x " * 5_000 + "\nTarget Metric: 999"
        receipt = build_observable_packing(QUESTION, [page(content)])[
            "content_free_receipt"
        ]
        self.assertTrue(
            receipt["candidate_requirement_coverage_not_less_than_prefix_baseline"]
        )
        self.assertEqual(receipt["orphan_selected_table_continuation_block_count"], 0)

    def test_receipt_resealed_tamper_fails(self) -> None:
        receipt = build_observable_packing(
            QUESTION, [page("boilerplate " * 600 + "\nOmega Republic [OMG]: 999")]
        )["content_free_receipt"]
        altered = copy.deepcopy(receipt)
        altered["long_page_mechanism_engaged"] = False
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_nondefault_cap_is_rejected_by_receipt_contract(self) -> None:
        policy = PackingPolicy(
            input_page_character_cap=10_000,
            output_page_character_cap=5_000,
        )
        with self.assertRaises(ValueError):
            build_observable_packing(QUESTION, [page("x" * 6_000)], policy=policy)


if __name__ == "__main__":
    unittest.main()
