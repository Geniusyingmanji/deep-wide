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
from deepwide_agent.v24383_active_verifier_query_runtime import (  # noqa: E402
    run_v24383_task,
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


class ActiveSearch:
    def __init__(self, *, active_mode: str = "support") -> None:
        self.active_mode = active_mode
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
        self.query_vectors: list[list[str]] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.query_vectors.append(values)
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        if self.search_invocations <= 2:
            prefix = "wavea" if self.search_invocations == 1 else "waveb"
            results = [
                {
                    "title": f"proposal {values[(index - 1) % len(values)]}",
                    "url": f"https://{prefix}{index}.example/item/{index}",
                    "fetch_url": f"https://{prefix}{index}.example/item/{index}",
                }
                for index in range(1, 9)
            ]
        else:
            results = [
                {
                    "title": "Alpha official Founding year 2025",
                    "url": "https://active-alpha.example/record",
                    "fetch_url": "https://active-alpha.example/record",
                },
                {
                    "title": "Beta official Founding year 2024",
                    "url": "https://active-beta.example/record",
                    "fetch_url": "https://active-beta.example/record",
                },
                {
                    "title": "generic public archive",
                    "url": "https://active-generic.example/record",
                    "fetch_url": "https://active-generic.example/record",
                },
            ]
        return [
            {
                "query": "private",
                "answer": "provider narrative",
                "results": results,
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        active = self.fetch_invocations == 3
        if not active:
            content = "Alpha was founded in 2025. Beta was established in 2024."
        elif self.active_mode == "support":
            content = (
                f"Alpha was founded in 2025, while Beta was founded in 2024. "
                f"{HIDDEN_MARKER}"
            )
        elif self.active_mode == "conflict":
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


class V24383ActiveVerifierQueryRuntimeTests(unittest.TestCase):
    def run_case(self, *, active_mode: str = "support"):
        model = Model()
        search = ActiveSearch(active_mode=active_mode)
        value = run_v24383_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_candidate_freeze_then_active_query_closes_budget(self) -> None:
        value, model, search = self.run_case()
        receipt = value["active_verifier_receipt"]
        self.assertEqual(receipt["proposal_search_batch_count"], 2)
        self.assertEqual(receipt["active_verifier_search_batch_count"], 1)
        self.assertEqual(receipt["total_search_batch_count"], 3)
        self.assertEqual(receipt["active_verifier_logical_query_count"], 2)
        self.assertEqual(receipt["total_logical_query_count"], 6)
        self.assertEqual(receipt["proposal_source_count"], 8)
        self.assertEqual(receipt["active_selected_source_count"], 2)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.calls, 3)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(receipt["candidate_changed_cells_after_active_verifier"], 2)
        self.assertGreater(receipt["verifier_semantic_projection_count"], 0)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_active_queries_are_candidate_conditioned_and_post_model(self) -> None:
        value, model, search = self.run_case()
        queries = value["private_replay_state"]["active_target_state"][
            "active_queries"
        ]
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("Alpha" in query and "2025" in query for query in queries))
        self.assertTrue(any("Beta" in query and "2024" in query for query in queries))
        self.assertEqual(search.query_vectors[-1], queries)
        self.assertTrue(
            value["active_verifier_receipt"][
                "active_queries_use_only_frozen_row_column_value"
            ]
        )
        prompt = "\n".join(user for _, user, _ in model.prompts)
        self.assertNotIn(HIDDEN_MARKER, prompt)

    def test_conflict_reverts_only_bound_target(self) -> None:
        value, _, _ = self.run_case(active_mode="conflict")
        receipt = value["active_verifier_receipt"]
        self.assertEqual(receipt["candidate_changed_cells_after_active_verifier"], 1)
        self.assertIn("| Alpha | Unknown |", value["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", value["candidate_prediction"])
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_missing_support_preserves_proposal_entropy_but_zero_utility(self) -> None:
        value, _, _ = self.run_case(active_mode="missing")
        receipt = value["active_verifier_receipt"]
        self.assertGreater(
            receipt["selected_proposal_conditional_entropy_reduction_nats"], 0
        )
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(receipt["candidate_changed_cells_after_active_verifier"], 0)

    def test_identity_candidate_spends_no_active_search_or_fetch(self) -> None:
        model = IdentityModel()
        search = ActiveSearch()
        value = run_v24383_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        receipt = value["active_verifier_receipt"]
        self.assertEqual(receipt["active_verifier_logical_query_count"], 0)
        self.assertEqual(receipt["active_verifier_search_batch_count"], 0)
        self.assertEqual(receipt["active_selected_source_count"], 0)
        self.assertEqual(receipt["total_fetch_calls"], 8)
        self.assertEqual(search.calls, 2)
        self.assertEqual(search.fetch_calls, 8)

    def test_private_replay_and_receipt_tamper_fail_closed(self) -> None:
        value, _, _ = self.run_case()
        for field in ("query", "lead", "page", "receipt"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "query":
                    altered["private_replay_state"]["active_target_state"][
                        "active_queries"
                    ][0] += " tamper"
                elif field == "lead":
                    altered["private_replay_state"]["selected_active_leads"][0][
                        "title"
                    ] += " tamper"
                elif field == "page":
                    altered["private_replay_state"]["active_fetch_batches"][0][
                        "results"
                    ][0]["raw_content"] += " tamper"
                else:
                    receipt = altered["active_verifier_receipt"]
                    receipt["active_selected_source_count"] += 1
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_rejected_before_effect(self) -> None:
        model = Model()
        search = ActiveSearch()
        with self.assertRaises(ValueError):
            run_v24383_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)


if __name__ == "__main__":
    unittest.main()
