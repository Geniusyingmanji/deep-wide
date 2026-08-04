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


class StructuredSearch(Search):
    def fetch_urls(self, requests):
        values = list(requests)
        self.fetch_invocations += 1
        self.fetch_calls += len(values)
        active = self.fetch_invocations == 3
        output = []
        for item in values:
            if active:
                content = (
                    "Alpha\nFounded | 2025\nWebsite | example\n\n"
                    "Beta\nFounded | 2024\nWebsite | example"
                )
            else:
                content = "Alpha publishes software. Beta publishes software."
            output.append(
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
            )
        return output


def legacy_case(search=None):
    model = IdentityModel(baseline=BASELINE)
    chosen = search or StructuredSearch()
    result = run_v24390_task(
        TASK,
        model=model,
        search=chosen,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=Clock(),
    )
    return result, model, chosen


class V24407StructuredUncertaintyRecoveryTests(unittest.TestCase):
    def test_zero_effect_recovery_converts_structured_active_pages(self) -> None:
        legacy, model, search = legacy_case()
        self.assertEqual(
            legacy["uncertainty_active_receipt"]["active_observation_count"], 0
        )
        before = (model.requests, search.calls, search.fetch_calls)
        recovered = recover_structured_uncertainty(legacy)
        receipt = recovered["structured_recovery_receipt"]
        self.assertEqual(before, (model.requests, search.calls, search.fetch_calls))
        self.assertEqual(receipt["legacy_active_observation_count"], 0)
        self.assertEqual(receipt["novel_structured_observation_count"], 2)
        self.assertEqual(receipt["combined_active_observation_count"], 2)
        self.assertEqual(receipt["recovered_safe_change_count"], 1)
        self.assertGreater(receipt["recovered_epistemic_credit_total_nats"], 0)
        self.assertGreater(receipt["recovered_decision_credit_total_nats"], 0)
        self.assertNotEqual(recovered["candidate_prediction"], BASELINE)
        self.assertTrue(receipt["structured_recovery_changed_output"])

    def test_legacy_prose_result_is_preserved_without_duplicate_credit(self) -> None:
        legacy, _, _ = legacy_case(Search(active_mode="support"))
        recovered = recover_structured_uncertainty(legacy)
        receipt = recovered["structured_recovery_receipt"]
        self.assertEqual(receipt["legacy_active_observation_count"], 2)
        self.assertEqual(receipt["novel_structured_observation_count"], 0)
        self.assertEqual(receipt["combined_active_observation_count"], 2)
        self.assertEqual(
            receipt["recovered_epistemic_credit_total_nats"],
            legacy["uncertainty_active_receipt"]["epistemic_credit_total_nats"],
        )
        self.assertEqual(
            recovered["candidate_prediction"], legacy["candidate_prediction"]
        )

    def test_missing_structured_relation_remains_identity(self) -> None:
        legacy, _, _ = legacy_case(Search(active_mode="missing"))
        recovered = recover_structured_uncertainty(legacy)
        receipt = recovered["structured_recovery_receipt"]
        self.assertEqual(receipt["combined_active_observation_count"], 0)
        self.assertEqual(receipt["recovered_safe_change_count"], 0)
        self.assertEqual(receipt["recovered_epistemic_credit_total_nats"], 0)
        self.assertEqual(recovered["candidate_prediction"], BASELINE)

    def test_parent_effect_counts_are_reused_exactly(self) -> None:
        legacy, _, _ = legacy_case()
        recovered = recover_structured_uncertainty(legacy)
        old = legacy["uncertainty_active_receipt"]
        receipt = recovered["structured_recovery_receipt"]
        self.assertEqual(receipt["parent_model_requests"], old["parent_model_requests"])
        self.assertEqual(
            receipt["parent_total_logical_queries"], old["total_logical_query_count"]
        )
        self.assertEqual(
            receipt["parent_total_search_batches"], old["total_search_batch_count"]
        )
        self.assertEqual(receipt["parent_total_fetch_calls"], old["total_fetch_calls"])
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(receipt["additional_logical_queries"], 0)
        self.assertEqual(receipt["additional_search_batches"], 0)
        self.assertEqual(receipt["additional_fetch_calls"], 0)

    def test_private_projection_posterior_prediction_and_receipt_tamper_fail(self) -> None:
        legacy, _, _ = legacy_case()
        recovered = recover_structured_uncertainty(legacy)
        for field in ("projection", "posterior", "prediction", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(recovered)
                if field == "projection":
                    altered["structured_active_projection"]["observations"][0][
                        "value"
                    ] = "2030"
                elif field == "posterior":
                    altered["structured_active_evidence_result"]["resolutions"][0][
                        "final_value"
                    ] = "2030"
                elif field == "prediction":
                    altered["candidate_prediction"] = BASELINE
                else:
                    altered["structured_recovery_receipt"][
                        "additional_model_requests"
                    ] = 1
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_public_receipt_is_label_blind_and_emits_no_private_content(self) -> None:
        legacy, _, _ = legacy_case()
        recovered = recover_structured_uncertainty(legacy)
        receipt = recovered["structured_recovery_receipt"]
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(
            receipt["task_private_page_observation_value_prediction_or_source_emitted"]
        )
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
