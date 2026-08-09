from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25019_production_distinct_coverage_selection as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import _lead_requests  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = """Use the official Acme Package Index public page.
<PACKAGES>
1. AlphaKit
2. BetaCore
3. GammaTools
</PACKAGES>
Column names: Package, Version, Published, License. Return one table only."""


def batches() -> list[dict]:
    return [
        {
            "query": "q1",
            "results": [
                {"url": "https://search.example/one", "title": "one"},
                {"url": "https://search.example/two", "title": "two"},
            ],
        },
        {
            "query": "q2",
            "results": [
                {"url": "https://search.example/three", "title": "three"},
                {"url": "https://search.example/four", "title": "four"},
            ],
        },
    ]


def pages(*, ambiguous: bool = False) -> list[dict]:
    links = [
        {"url": "AlphaKit/index.html", "text": "alpha"},
        {"url": "BetaCore/index.html", "text": "beta"},
        {"url": "GammaTools/index.html", "text": "gamma"},
    ]
    if ambiguous:
        links.insert(0, {"url": "AlphaKit/BetaCore/index.html", "text": "ambiguous"})
    return [
        {
            "query": "first",
            "results": [
                {
                    "url": "https://packages.acme.example/web/packages/",
                    "requested_url": "https://packages.acme.example/web/packages/",
                    "raw_content": "index",
                    "page_links": links,
                }
            ],
        }
    ]


class ProductionDistinctCoverageSelectionTests(unittest.TestCase):
    def test_control_exactly_replays_legacy_and_candidate_has_same_cost(self) -> None:
        value = target.select_production_second_wave(
            pages(), batches(), question=QUESTION, cap=4
        )
        legacy = _lead_requests(batches(), 4)
        self.assertEqual(value["control"], legacy)
        self.assertEqual(len(value["candidate"]), len(value["control"]))
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["control_new_distinct_identity_count"], 0)
        self.assertEqual(receipt["candidate_new_distinct_identity_count"], 3)
        self.assertEqual(receipt["new_distinct_identity_gain"], 3)
        self.assertTrue(receipt["mechanism_engaged"])

    def test_existing_search_identity_is_preserved_before_child_remainder(self) -> None:
        raw = batches()
        raw[0]["results"][0]["url"] = (
            "https://packages.acme.example/search/AlphaKit/index.html"
        )
        value = target.select_production_second_wave(
            pages(), raw, question=QUESTION, cap=4
        )
        candidate_urls = [row["url"] for row in value["candidate"]]
        self.assertEqual(candidate_urls[0], raw[0]["results"][0]["url"])
        self.assertEqual(
            value["content_free_receipt"]["candidate_new_distinct_identity_count"],
            3,
        )

    def test_non_multi_identity_question_is_exact_handoff(self) -> None:
        question = "Find <PACKAGE>AlphaKit</PACKAGE> from the official Acme Index."
        value = target.select_production_second_wave(
            pages(), batches(), question=question, cap=4
        )
        self.assertEqual(value["candidate"], value["control"])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["visible_identity_count"], 0)
        self.assertFalse(receipt["strategy_eligible"])
        self.assertFalse(receipt["selection_changed"])

    def test_excluded_first_wave_url_matches_frozen_control_filter(self) -> None:
        raw = batches()
        excluded = raw[0]["results"][0]["url"]
        value = target.select_production_second_wave(
            pages(), raw, question=QUESTION, cap=4, exclude_urls={excluded}
        )
        legacy = [
            row for row in _lead_requests(raw, 4) if row["url"] != excluded
        ]
        self.assertEqual(value["control"], legacy)
        self.assertEqual(len(value["candidate"]), len(legacy))

    def test_ambiguous_child_receives_no_identity_credit(self) -> None:
        value = target.select_production_second_wave(
            pages(ambiguous=True), batches(), question=QUESTION, cap=4
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["ambiguous_identity_child_link_count"], 1)
        self.assertEqual(receipt["candidate_new_distinct_identity_count"], 3)

    def test_resealed_cost_or_gain_tamper_is_rejected(self) -> None:
        receipt = copy.deepcopy(
            target.select_production_second_wave(
                pages(), batches(), question=QUESTION, cap=4
            )["content_free_receipt"]
        )
        receipt["candidate_selected_url_count"] = 3
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            target.validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
