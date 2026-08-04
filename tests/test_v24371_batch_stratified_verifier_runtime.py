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
from deepwide_agent.v24362_two_verifier_partition_runtime import (  # noqa: E402
    _partition_leads as frozen_partition_leads,
)
from deepwide_agent.v24371_batch_stratified_verifier_runtime import (  # noqa: E402
    BatchStratifiedPrefilterSearchClient,
    run_v24371_task,
    validate_result,
)
from test_v24367_target_segment_verifier_runtime import (  # noqa: E402
    HIDDEN_MARKER,
    Model,
    TASK,
)
from test_v24342_semantic_active_runtime import Clock, limits  # noqa: E402


SEED = "c" * 64


class Search:
    def __init__(
        self,
        *,
        hidden_mode: str = "support",
    ) -> None:
        self.hidden_mode = hidden_mode
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.search_invocations = 0
        self.fetch_invocations = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        query_values = list(queries)
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        prefix = "alpha" if self.search_invocations == 1 else "beta"
        results = []
        for index in range(1, 13):
            query_word = query_values[(index - 1) % len(query_values)]
            results.append(
                {
                    "title": f"{prefix} {query_word} public record {index}",
                    "url": f"https://{prefix}{index}.example/item/{index}",
                    "fetch_url": f"https://{prefix}{index}.example/item/{index}",
                }
            )
        return [
            {
                "query": f"private-{prefix}",
                "answer": "private provider narrative",
                "results": results,
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        hidden = self.fetch_invocations == 3
        if not hidden:
            content = "Alpha was founded in 2025. Beta was established in 2024."
        elif self.hidden_mode == "support":
            content = (
                f"Alpha was founded in 2025, while Beta was founded in 2024. "
                f"{HIDDEN_MARKER}"
            )
        elif self.hidden_mode == "conflict":
            content = (
                f"Alpha was founded in 2026, while Beta was founded in 2024. "
                f"{HIDDEN_MARKER}"
            )
        else:
            content = f"Alpha and Beta publish documentation. {HIDDEN_MARKER}"
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


class V24371BatchStratifiedVerifierRuntimeTests(unittest.TestCase):
    def run_case(self, *, hidden_mode: str = "support"):
        model = Model()
        search = Search(hidden_mode=hidden_mode)
        value = run_v24371_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_full_capacity_is_five_plus_five_with_one_verifier_per_batch(self) -> None:
        value, model, search = self.run_case()
        receipt = value["batch_stratification_receipt"]
        parent = value["parent_result"]
        verifier = parent["target_segment_verifier_receipt"]
        self.assertEqual(receipt["raw_batch_unique_host_counts"], [12, 12])
        self.assertEqual(receipt["selected_batch_host_counts"], [5, 5])
        self.assertEqual(receipt["proposal_batch_host_counts"], [4, 4])
        self.assertEqual(receipt["verifier_batch_host_counts"], [1, 1])
        self.assertTrue(receipt["full_capacity_batch_stratification_satisfied"])
        self.assertEqual(verifier["parent_fetch_calls"], 8)
        self.assertEqual(verifier["hidden_verifier_fetch_calls"], 2)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.calls, 2)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(verifier["candidate_changed_cells_after_hidden_verifier"], 2)
        self.assertGreater(verifier["utility_aligned_entropy_credit_nats"], 0)

    def test_old_first_ten_selection_excludes_the_second_batch(self) -> None:
        search = Search()
        client = BatchStratifiedPrefilterSearchClient(
            search, partition_seed_sha256=SEED
        )
        client.search_many(["one", "two"], max_results=3)
        client.search_many(["three", "four"], max_results=3)
        state = client.private_replay_state()
        old_vector = [
            *state["raw_batch_leads"][0],
            *state["raw_batch_leads"][1],
        ][:10]
        old_proposal, old_verifier, _ = frozen_partition_leads(
            old_vector, partition_seed_sha256=SEED
        )
        old_sources = {
            row["url"].split("//", 1)[1].split(".", 1)[0]
            for row in [*old_proposal, *old_verifier]
        }
        self.assertTrue(all(source.startswith("alpha") for source in old_sources))
        selected = state["selected_batch_leads"]
        self.assertEqual([len(batch) for batch in selected], [5, 5])

    def test_independent_conflict_still_reverts_only_its_bound_target(self) -> None:
        value, _, _ = self.run_case(hidden_mode="conflict")
        receipt = value["parent_result"]["target_segment_verifier_receipt"]
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"] > 0, True)
        self.assertIn("| Alpha | Unknown |", value["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", value["candidate_prediction"])

    def test_missing_support_preserves_proposal_entropy_but_zero_utility(self) -> None:
        value, _, _ = self.run_case(hidden_mode="missing")
        receipt = value["parent_result"]["target_segment_verifier_receipt"]
        self.assertGreater(
            receipt["selected_proposal_conditional_entropy_reduction_nats"], 0
        )
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)

    def test_tamper_fails_closed(self) -> None:
        value, _, _ = self.run_case()
        for field in ("query", "raw", "selected", "receipt", "parent"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "query":
                    altered["private_replay_state"]["query_batches"][0][0] += " tamper"
                elif field == "raw":
                    altered["private_replay_state"]["raw_batch_leads"][0][0][
                        "title"
                    ] += " tamper"
                elif field == "selected":
                    altered["private_replay_state"]["selected_batch_leads"][1][0][
                        "url"
                    ] = "https://tampered.example/item"
                elif field == "receipt":
                    receipt = altered["batch_stratification_receipt"]
                    receipt["verifier_batch_host_counts"] = [2, 0]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                else:
                    altered["parent_result"]["candidate_prediction"] = "tamper"
                    parent = altered["parent_result"]
                    parent.pop("result_sha256")
                    parent["result_sha256"] = payload_sha256(parent)
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaises(ValueError):
            run_v24371_task(
                {**TASK, "split": "forbidden"},
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
        receipt = value["batch_stratification_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for private in (
            "Alpha",
            "Beta",
            "2025",
            "alpha1.example",
            "public record",
        ):
            self.assertNotIn(private, encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
