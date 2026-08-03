from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24355_explicit_partition_runtime import (  # noqa: E402
    run_v24355_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    Model,
    TASK,
    limits,
)


SEED = "b" * 64


class Search:
    def __init__(
        self,
        *,
        hidden_conflict: bool = False,
        hidden_failure: bool = False,
        proposal_failure: bool = False,
    ) -> None:
        self.hidden_conflict = hidden_conflict
        self.hidden_failure = hidden_failure
        self.proposal_failure = proposal_failure
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.fetch_invocations = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, **kwargs):
        del queries, kwargs
        self.calls += 1
        self.tool_calls += 1
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": f"record-{index}",
                        "url": f"https://source{index}.example/item",
                        "fetch_url": f"https://source{index}.example/item",
                    }
                    for index in range(1, 11)
                ],
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        hidden = self.fetch_invocations == 3
        output = []
        for index, item in enumerate(values):
            host = item["url"].split("/")[2]
            if hidden and self.hidden_failure:
                self.fetch_failures += 1
                content = ""
            elif hidden and self.hidden_conflict:
                content = f"Alpha was founded in 2024 according to {host}."
            elif not hidden and self.proposal_failure and index == 0 and self.fetch_invocations == 1:
                self.fetch_failures += 1
                content = ""
            else:
                content = f"Alpha was founded in 2025 according to {host}."
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


class V24355ExplicitPartitionRuntimeTests(unittest.TestCase):
    def run_case(self, *, search: Search | None = None):
        model = Model(baseline=BASELINE_UNKNOWN)
        search = search or Search()
        value = run_v24355_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_one_hidden_host_retains_parent_support_and_credit(self) -> None:
        value, model, search = self.run_case()
        receipt = value["hidden_verifier_receipt"]
        partition = receipt["partition_receipt"]
        self.assertEqual(partition["proposal_source_count"], 9)
        self.assertEqual(partition["verifier_source_count"], 1)
        self.assertEqual(partition["verifier_source_cap"], 1)
        self.assertIn("| Alpha | 2025 |", value["candidate_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_before_hidden_verifier"], 1)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(search.fetch_invocations, 3)

    def test_failed_proposal_page_does_not_repartition_successful_pages(self) -> None:
        value, _, _ = self.run_case(search=Search(proposal_failure=True))
        receipt = value["hidden_verifier_receipt"]
        catalog = value["private_replay_state"]["utility_catalog"]
        self.assertTrue(receipt["observed_pages_respect_frozen_partition"])
        self.assertLess(
            len(catalog["observed_proposal_source_key_sha256s"]),
            len(catalog["expected_proposal_source_key_sha256s"]),
        )
        self.assertIn("| Alpha | 2025 |", value["candidate_prediction"])

    def test_hidden_conflict_reverts_without_new_model_call(self) -> None:
        value, model, _ = self.run_case(search=Search(hidden_conflict=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["hidden_verifier_reverted_cells"], 1)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(model.requests, 3)

    def test_missing_hidden_page_fails_closed_without_partition_mismatch(self) -> None:
        value, _, _ = self.run_case(search=Search(hidden_failure=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertTrue(receipt["observed_pages_respect_frozen_partition"])
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_hidden_page_never_enters_parent_prompt(self) -> None:
        value, model, _ = self.run_case()
        hidden = value["private_replay_state"]["verifier_pages"]
        prompt_text = "\n".join(user for _, user, _ in model.prompts)
        parent_private = value["parent_result"]["semantic_result"][
            "semantic_active_private_state"
        ]
        parent_hosts = {
            page["host"]
            for page in [
                *parent_private["raw_core_pages"],
                *parent_private["raw_reserve_pages"],
            ]
        }
        for page in hidden:
            self.assertNotIn(page["host"], parent_hosts)
            self.assertNotIn(page["content"], prompt_text)

    def test_private_and_public_tamper_fail_replay(self) -> None:
        value, _, _ = self.run_case()
        for field in ("catalog", "batch", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "catalog":
                    altered["private_replay_state"]["utility_catalog"][
                        "utility_sets"
                    ][0]["proposal_support_set_id"] = "f" * 64
                elif field == "batch":
                    altered["private_replay_state"]["verifier_fetch_batches"][0][
                        "results"
                    ][0]["raw_content"] += " tamper"
                else:
                    altered["hidden_verifier_receipt"][
                        "candidate_changed_cells_after_hidden_verifier"
                    ] = 0
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_key_rejected_before_effect(self) -> None:
        model = Model(baseline=BASELINE_UNKNOWN)
        search = Search()
        with self.assertRaises(ValueError):
            run_v24355_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_public_receipt_is_content_free_and_label_blind(self) -> None:
        value, _, _ = self.run_case()
        receipt = value["hidden_verifier_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        self.assertNotIn("Alpha", encoded)
        self.assertNotIn("source1.example", encoded)
        self.assertNotIn("Alpha was founded", encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
