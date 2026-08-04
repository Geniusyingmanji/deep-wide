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
from deepwide_agent.v24378_adaptive_heldout_verifier_runtime import (  # noqa: E402
    AdaptiveHeldoutVerifierSearchClient,
    run_v24378_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import Clock, limits  # noqa: E402
from test_v24367_target_segment_verifier_runtime import (  # noqa: E402
    BASELINE,
    HIDDEN_MARKER,
    Model,
    SEED,
    TASK,
)


class AdaptiveSearch:
    def __init__(self, *, hidden_mode: str = "support") -> None:
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
        values = list(queries)
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        prefix = "wavea" if self.search_invocations == 1 else "waveb"
        targets = ["Alpha", "Beta"]
        results = []
        for index in range(1, 13):
            if index <= 4:
                title = f"official {values[(index - 1) % len(values)]} record"
            elif index == 5:
                title = targets[self.search_invocations - 1]
            else:
                title = f"generic public archive {index}"
            results.append(
                {
                    "title": title,
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


class IdentityModel(Model):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.requests < 2:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        self.prompts.append((system, user, json_mode))
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return json.dumps({"candidate_table": BASELINE, "cell_support": []})


class V24378AdaptiveHeldoutVerifierRuntimeTests(unittest.TestCase):
    def run_case(self, *, hidden_mode: str = "support"):
        model = Model()
        search = AdaptiveSearch(hidden_mode=hidden_mode)
        value = run_v24378_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_post_candidate_selection_closes_four_ten_three_budget(self) -> None:
        value, model, search = self.run_case()
        receipt = value["adaptive_verifier_receipt"]
        self.assertEqual(receipt["logical_query_count"], 4)
        self.assertEqual(receipt["proposal_batch_host_counts"], [4, 4])
        self.assertEqual(receipt["selected_verifier_batch_host_counts"], [1, 1])
        self.assertEqual(receipt["parent_fetch_calls"], 8)
        self.assertEqual(receipt["hidden_verifier_fetch_calls"], 2)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.calls, 2)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(receipt["candidate_changed_cells_before_hidden_verifier"], 2)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 2)
        self.assertGreater(receipt["verifier_semantic_projection_count"], 0)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_candidate_targets_select_entity_titles_from_heldout_pool(self) -> None:
        value, _, _ = self.run_case()
        selected = value["private_replay_state"]["selected_verifier_leads"]
        self.assertIn("Alpha", selected[0][0]["title"])
        self.assertIn("Beta", selected[1][0]["title"])
        receipt = value["adaptive_verifier_receipt"]
        self.assertEqual(
            receipt["selected_verifier_exact_row_phrase_match_count"], 2
        )
        self.assertFalse(receipt["verifier_page_content_observed_before_selection"])
        self.assertFalse(
            receipt["verifier_pages_used_for_candidate_generation_or_model_prompt"]
        )

    def test_conflict_reverts_only_bound_target(self) -> None:
        value, _, _ = self.run_case(hidden_mode="conflict")
        receipt = value["adaptive_verifier_receipt"]
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertIn("| Alpha | Unknown |", value["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", value["candidate_prediction"])
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_missing_support_preserves_proposal_entropy_but_zero_utility(self) -> None:
        value, _, _ = self.run_case(hidden_mode="missing")
        receipt = value["adaptive_verifier_receipt"]
        self.assertGreater(
            receipt["selected_proposal_conditional_entropy_reduction_nats"], 0
        )
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)

    def test_identity_candidate_spends_no_verifier_fetch(self) -> None:
        model = IdentityModel()
        search = AdaptiveSearch()
        value = run_v24378_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        receipt = value["adaptive_verifier_receipt"]
        self.assertEqual(receipt["candidate_target_count"], 0)
        self.assertEqual(receipt["selected_verifier_source_count"], 0)
        self.assertEqual(receipt["hidden_verifier_fetch_calls"], 0)
        self.assertEqual(receipt["total_fetch_calls"], 8)
        self.assertEqual(search.fetch_calls, 8)

    def test_private_replay_and_public_receipt_tamper_fail_closed(self) -> None:
        value, _, _ = self.run_case()
        for field in ("raw", "proposal", "selected", "page", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "raw":
                    altered["private_replay_state"]["selection_state"][
                        "raw_batch_leads"
                    ][0][0]["title"] += " tamper"
                elif field == "proposal":
                    altered["private_replay_state"]["selection_state"][
                        "proposal_batch_leads"
                    ][0][0]["title"] += " tamper"
                elif field == "selected":
                    altered["private_replay_state"]["selected_verifier_leads"][0][0][
                        "title"
                    ] += " tamper"
                elif field == "page":
                    altered["private_replay_state"]["verifier_fetch_batches"][0][
                        "results"
                    ][0]["raw_content"] += " tamper"
                else:
                    receipt = altered["adaptive_verifier_receipt"]
                    receipt["selected_verifier_exact_row_phrase_match_count"] += 1
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = Model()
        search = AdaptiveSearch()
        with self.assertRaises(ValueError):
            run_v24378_task(
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
        encoded = json.dumps(value["adaptive_verifier_receipt"], ensure_ascii=False)
        for private in (
            "Alpha",
            "Beta",
            "2025",
            "wavea5.example",
            "generic public archive",
        ):
            self.assertNotIn(private, encoded)
        self.assertFalse(
            value["adaptive_verifier_receipt"][
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
