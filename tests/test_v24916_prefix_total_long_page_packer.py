from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24911_long_page_evidence_packer import PackingPolicy  # noqa: E402
from deepwide_agent.v24916_prefix_total_long_page_packer import (  # noqa: E402
    build_prefix_total_packing,
    validate_receipt,
)


QUESTION = "Return one table. Columns: Entity, Value"


def page(content: str) -> dict[str, str]:
    return {
        "title": "Official",
        "url": "https://official.example/data",
        "content": content,
    }


def overflow_content() -> str:
    return (("Entity Value " + "x" * 40) + "\n\n") * 200


class V24916PrefixTotalLongPagePackerTests(unittest.TestCase):
    def test_diagnosed_overflow_falls_back_to_exact_prefix(self) -> None:
        content = overflow_content()
        result = build_prefix_total_packing(QUESTION, [page(content)])
        receipt = result["content_free_receipt"]
        self.assertTrue(receipt["structural_cap_totality_fallback_applied"])
        self.assertTrue(receipt["fallback_trigger_was_exact_diagnosed_overflow"])
        self.assertTrue(receipt["fallback_projection_is_exact_stable_5k_prefix"])
        self.assertIn(content[:5_000], result["projection"])
        self.assertLessEqual(receipt["output_active_content_characters"], 5_000)

    def test_nonoverflow_long_page_keeps_query_aware_mechanism(self) -> None:
        content = "boilerplate " * 600 + "\nOmega Republic [OMG]: 999"
        result = build_prefix_total_packing(
            "Return Omega Republic [OMG] Value", [page(content)]
        )
        receipt = result["content_free_receipt"]
        self.assertFalse(receipt["structural_cap_totality_fallback_applied"])
        self.assertTrue(receipt["long_page_mechanism_engaged"])
        self.assertIn("Omega Republic [OMG]: 999", result["projection"])

    def test_short_page_is_byte_identical(self) -> None:
        content = "Entity Value: 999"
        result = build_prefix_total_packing(QUESTION, [page(content)])
        receipt = result["content_free_receipt"]
        self.assertEqual(receipt["original_short_page_count"], 1)
        self.assertTrue(receipt["original_short_page_content_byte_identity_preserved"])
        self.assertIn(content, result["projection"])

    def test_unrelated_runtime_error_is_not_swallowed(self) -> None:
        with mock.patch(
            "deepwide_agent.v24916_prefix_total_long_page_packer.parent.build_observable_packing",
            side_effect=RuntimeError("unrelated failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unrelated failure"):
                build_prefix_total_packing(QUESTION, [page(overflow_content())])

    def test_receipt_resealed_tamper_fails(self) -> None:
        receipt = build_prefix_total_packing(
            QUESTION, [page(overflow_content())]
        )["content_free_receipt"]
        altered = copy.deepcopy(receipt)
        altered["long_page_mechanism_engaged"] = True
        altered.pop("receipt_payload_sha256")
        from deepwide_agent.v24911_long_page_evidence_packer import payload_sha256

        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_nonproduction_caps_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_prefix_total_packing(
                QUESTION,
                [page(overflow_content())],
                policy=PackingPolicy(output_page_character_cap=4_999),
            )


if __name__ == "__main__":
    unittest.main()
