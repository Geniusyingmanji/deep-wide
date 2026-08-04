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
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    run_v24390_task,
)
from deepwide_agent.v24407_structured_uncertainty_recovery import (  # noqa: E402
    recover_structured_uncertainty,
)
from deepwide_agent.v24429_title_anchor_uncertainty_recovery import (  # noqa: E402
    recover_title_anchor_uncertainty,
    validate_result,
)
from test_v24342_semantic_active_runtime import Clock, limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    BASELINE,
    IdentityModel,
    Search,
    SEED,
    TASK,
)


class TitleOnlySearch(Search):
    def search_many(self, queries, **kwargs):
        result = super().search_many(queries, **kwargs)
        if self.search_invocations == 3:
            result[0]["results"] = [
                {
                    "title": "Alpha - official history",
                    "url": "https://active-alpha-one.example/record",
                    "fetch_url": "https://active-alpha-one.example/record",
                },
                {
                    "title": "Alpha | historical archive",
                    "url": "https://active-alpha-two.example/record",
                    "fetch_url": "https://active-alpha-two.example/record",
                },
            ]
        return result

    def fetch_urls(self, requests):
        values = list(requests)
        self.fetch_invocations += 1
        self.fetch_calls += len(values)
        active = self.fetch_invocations == 3
        content = "Founded | 2025" if active else "Alpha and Beta publish software."
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "requested_url": item["url"],
                        "raw_content": content,
                    }
                ],
            }
            for item in values
        ]


class ConflictingTitleSearch(TitleOnlySearch):
    def fetch_urls(self, requests):
        result = super().fetch_urls(requests)
        if self.fetch_invocations == 3:
            for index, batch in enumerate(result):
                batch["results"][0]["raw_content"] = f"Founded | {2025 + index}"
        return result


class ParentSupportTitleConflictSearch(TitleOnlySearch):
    def fetch_urls(self, requests):
        result = super().fetch_urls(requests)
        if self.fetch_invocations == 3:
            for batch in result:
                batch["results"][0]["raw_content"] = (
                    "Alpha was founded in 2025.\nFounded | 2026"
                )
        return result


def parent_case(search=None):
    model = IdentityModel(baseline=BASELINE)
    chosen = search or TitleOnlySearch()
    legacy = run_v24390_task(
        TASK,
        model=model,
        search=chosen,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=Clock(),
    )
    structured = recover_structured_uncertainty(legacy)
    return structured, model, chosen


class V24429TitleAnchorUncertaintyRecoveryTests(unittest.TestCase):
    def test_title_anchor_converts_two_labelled_pages_into_decision_credit(self) -> None:
        structured, model, search = parent_case()
        parent_receipt = structured["structured_recovery_receipt"]
        self.assertEqual(parent_receipt["combined_active_observation_count"], 0)
        before = (model.requests, search.calls, search.fetch_calls)
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
        self.assertEqual(before, (model.requests, search.calls, search.fetch_calls))
        self.assertEqual(receipt["unique_title_anchor_page_count"], 2)
        self.assertEqual(receipt["title_anchor_projection_count"], 2)
        self.assertEqual(receipt["novel_title_anchor_observation_count"], 2)
        self.assertEqual(receipt["title_recovered_safe_change_count"], 1)
        self.assertGreater(receipt["title_recovered_epistemic_credit_total_nats"], 0)
        self.assertGreater(receipt["title_recovered_decision_credit_total_nats"], 0)
        self.assertIn("| Alpha | 2025 |", recovered["candidate_prediction"])
        self.assertTrue(receipt["title_recovery_changed_parent_output"])

    def test_conflicting_title_sources_remain_unresolved(self) -> None:
        structured, _, _ = parent_case(ConflictingTitleSearch())
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
        self.assertEqual(receipt["title_recovered_safe_change_count"], 0)
        self.assertEqual(receipt["title_recovered_decision_credit_total_nats"], 0)
        self.assertEqual(recovered["candidate_prediction"], BASELINE)

    def test_title_conflict_may_revert_parent_change_to_baseline(self) -> None:
        structured, _, _ = parent_case(ParentSupportTitleConflictSearch())
        parent_receipt = structured["structured_recovery_receipt"]
        self.assertEqual(parent_receipt["recovered_safe_change_count"], 1)
        self.assertNotEqual(structured["candidate_prediction"], BASELINE)
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
        self.assertTrue(receipt["title_recovery_changed_parent_output"])
        self.assertEqual(receipt["title_candidate_changed_cell_count"], 0)
        self.assertEqual(receipt["title_recovered_safe_change_count"], 0)
        self.assertEqual(recovered["candidate_prediction"], BASELINE)

    def test_title_anchor_without_exact_label_preserves_parent_result(self) -> None:
        structured, _, _ = parent_case(Search(active_mode="missing"))
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
        self.assertEqual(receipt["unique_title_anchor_page_count"], 2)
        self.assertEqual(receipt["title_anchor_projection_count"], 0)
        self.assertEqual(
            recovered["candidate_prediction"], structured["candidate_prediction"]
        )
        self.assertFalse(receipt["title_recovery_changed_parent_output"])

    def test_parent_projection_and_effect_counts_are_preserved(self) -> None:
        structured, _, _ = parent_case()
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
        self.assertEqual(
            recovered["title_anchor_projection"]["parent_projection"],
            structured["structured_active_projection"],
        )
        parent_receipt = structured["structured_recovery_receipt"]
        for new, old in (
            ("parent_model_requests", "parent_model_requests"),
            ("parent_total_logical_queries", "parent_total_logical_queries"),
            ("parent_total_search_batches", "parent_total_search_batches"),
            ("parent_total_fetch_calls", "parent_total_fetch_calls"),
        ):
            self.assertEqual(receipt[new], parent_receipt[old])
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(receipt["additional_logical_queries"], 0)
        self.assertEqual(receipt["additional_search_batches"], 0)
        self.assertEqual(receipt["additional_fetch_calls"], 0)

    def test_projection_posterior_prediction_and_receipt_tamper_fail(self) -> None:
        structured, _, _ = parent_case()
        recovered = recover_title_anchor_uncertainty(structured)
        for field in ("projection", "posterior", "prediction", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(recovered)
                if field == "projection":
                    altered["title_anchor_projection"]["observations"][0][
                        "value"
                    ] = "2030"
                elif field == "posterior":
                    altered["title_anchor_active_evidence_result"]["resolutions"][0][
                        "final_value"
                    ] = "2030"
                elif field == "prediction":
                    altered["candidate_prediction"] = BASELINE
                else:
                    altered["title_anchor_recovery_receipt"][
                        "additional_model_requests"
                    ] = 1
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_public_receipt_is_label_blind_and_content_free(self) -> None:
        structured, _, _ = parent_case()
        recovered = recover_title_anchor_uncertainty(structured)
        receipt = recovered["title_anchor_recovery_receipt"]
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
