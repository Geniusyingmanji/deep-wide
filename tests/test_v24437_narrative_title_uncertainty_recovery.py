from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24429_title_anchor_uncertainty_recovery import (  # noqa: E402
    recover_title_anchor_uncertainty,
)
from deepwide_agent.v24437_narrative_title_uncertainty_recovery import (  # noqa: E402
    recover_narrative_title_uncertainty,
    validate_result,
)
from test_v24390_uncertainty_active_evidence_runtime import BASELINE, Search  # noqa: E402
from test_v24429_title_anchor_uncertainty_recovery import (  # noqa: E402
    ConflictingTitleSearch,
    TitleOnlySearch,
    parent_case,
)


class NarrativeOnlySearch(TitleOnlySearch):
    def fetch_urls(self, requests):
        result = super().fetch_urls(requests)
        if self.fetch_invocations == 3:
            for batch in result:
                batch["results"][0]["raw_content"] = (
                    "The product was founded in 2025 and later expanded."
                )
        return result


class ConflictingNarrativeSearch(NarrativeOnlySearch):
    def fetch_urls(self, requests):
        result = super().fetch_urls(requests)
        if self.fetch_invocations == 3:
            for index, batch in enumerate(result):
                batch["results"][0]["raw_content"] = (
                    f"The product was founded in {2025 + index}."
                )
        return result


def recover(search=None):
    structured, model, chosen = parent_case(search or NarrativeOnlySearch())
    anchored = recover_title_anchor_uncertainty(structured)
    narrative = recover_narrative_title_uncertainty(anchored)
    return narrative, anchored, model, chosen


class V24437NarrativeTitleUncertaintyRecoveryTests(unittest.TestCase):
    def test_narrative_evidence_converts_to_decision_credit_without_effects(self) -> None:
        narrative, anchored, model, search = recover()
        parent_receipt = anchored["title_anchor_recovery_receipt"]
        receipt = narrative["narrative_recovery_receipt"]
        self.assertEqual(parent_receipt["title_anchor_projection_count"], 0)
        self.assertEqual(receipt["narrative_projection_count"], 2)
        self.assertEqual(receipt["novel_narrative_observation_count"], 2)
        self.assertEqual(receipt["narrative_recovered_safe_change_count"], 1)
        self.assertGreater(
            receipt["narrative_recovered_epistemic_credit_total_nats"], 0
        )
        self.assertGreater(
            receipt["narrative_recovered_decision_credit_total_nats"], 0
        )
        self.assertIn("| Alpha | 2025 |", narrative["candidate_prediction"])
        self.assertNotEqual(
            narrative["candidate_prediction"], anchored["candidate_prediction"]
        )
        self.assertEqual(model.requests, receipt["parent_model_requests"])
        self.assertEqual(search.calls, receipt["parent_total_search_batches"])
        self.assertEqual(search.fetch_calls, receipt["parent_total_fetch_calls"])

    def test_key_value_parent_is_preserved_without_duplicate_narrative_credit(self) -> None:
        narrative, anchored, _, _ = recover(TitleOnlySearch())
        receipt = narrative["narrative_recovery_receipt"]
        self.assertEqual(receipt["parent_title_anchor_projection_count"], 2)
        self.assertEqual(receipt["narrative_projection_count"], 0)
        self.assertEqual(receipt["novel_narrative_observation_count"], 0)
        self.assertEqual(
            narrative["candidate_prediction"], anchored["candidate_prediction"]
        )

    def test_conflicting_narrative_sources_remain_unresolved(self) -> None:
        narrative, anchored, _, _ = recover(ConflictingNarrativeSearch())
        receipt = narrative["narrative_recovery_receipt"]
        self.assertEqual(receipt["narrative_recovered_safe_change_count"], 0)
        self.assertEqual(receipt["narrative_recovered_decision_credit_total_nats"], 0)
        self.assertEqual(narrative["candidate_prediction"], BASELINE)
        self.assertEqual(anchored["candidate_prediction"], BASELINE)

    def test_no_explicit_relation_preserves_parent(self) -> None:
        narrative, anchored, _, _ = recover(Search(active_mode="missing"))
        receipt = narrative["narrative_recovery_receipt"]
        self.assertEqual(receipt["narrative_projection_count"], 0)
        self.assertEqual(
            narrative["candidate_prediction"], anchored["candidate_prediction"]
        )

    def test_parent_projection_and_effect_counts_are_preserved(self) -> None:
        narrative, anchored, _, _ = recover()
        receipt = narrative["narrative_recovery_receipt"]
        self.assertEqual(
            narrative["narrative_title_projection"]["parent_projection"],
            anchored["title_anchor_projection"],
        )
        parent_receipt = anchored["title_anchor_recovery_receipt"]
        for name in (
            "parent_model_requests",
            "parent_total_logical_queries",
            "parent_total_search_batches",
            "parent_total_fetch_calls",
        ):
            self.assertEqual(receipt[name], parent_receipt[name])
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_fetch_calls",
        ):
            self.assertEqual(receipt[name], 0)

    def test_projection_posterior_prediction_or_receipt_tamper_fails(self) -> None:
        narrative, _, _, _ = recover()
        for field in ("projection", "posterior", "prediction", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(narrative)
                if field == "projection":
                    altered["narrative_title_projection"][
                        "narrative_title_projections"
                    ][0]["value"] = "2030"
                elif field == "posterior":
                    altered["narrative_active_evidence_result"]["resolutions"][0][
                        "final_value"
                    ] = "2030"
                elif field == "prediction":
                    altered["candidate_prediction"] = BASELINE
                else:
                    altered["narrative_recovery_receipt"][
                        "additional_model_requests"
                    ] = 1
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_public_receipt_is_label_blind_content_free_and_partitioned(self) -> None:
        narrative, _, _, _ = recover()
        receipt = narrative["narrative_recovery_receipt"]
        self.assertTrue(receipt["narrative_reason_partition_exact"])
        self.assertEqual(
            sum(receipt["narrative_reason_counts"].values()),
            receipt["narrative_page_target_pair_count"],
        )
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(
            receipt[
                "task_private_title_page_observation_value_prediction_or_source_emitted"
            ]
        )
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
