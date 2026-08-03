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
from deepwide_agent.v24351_hidden_verifier_runtime import (  # noqa: E402
    run_v24351_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    Model,
    TASK,
    limits,
)


SEED = "5" * 64
VERIFIER_HOSTS = frozenset({"source3.example", "source10.example"})


class Search:
    def __init__(self, *, verifier_conflict: bool = False, verifier_failure: bool = False) -> None:
        self.verifier_conflict = verifier_conflict
        self.verifier_failure = verifier_failure
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
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
        values = list(requests)
        self.fetch_calls += len(values)
        output = []
        for item in values:
            host = item["url"].split("/")[2]
            if self.verifier_failure and host in VERIFIER_HOSTS:
                self.fetch_failures += 1
                content = ""
            elif self.verifier_conflict and host in VERIFIER_HOSTS:
                content = (
                    f"Alpha was founded in 2024 according to independent record {host}."
                )
            else:
                content = (
                    f"Alpha was founded in 2025 according to independent record {host}."
                )
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


class V24351HiddenVerifierRuntimeTests(unittest.TestCase):
    def run_case(self, *, search: Search | None = None):
        model = Model(baseline=BASELINE_UNKNOWN)
        search = search or Search()
        value = run_v24351_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_hidden_verifier_retains_independently_supported_change(self) -> None:
        value, model, search = self.run_case()
        receipt = value["hidden_verifier_receipt"]
        verifier_leads = value["private_replay_state"]["partition"]["verifier_leads"]
        self.assertEqual(
            {lead["url"].split("/")[2] for lead in verifier_leads},
            VERIFIER_HOSTS,
        )
        self.assertIn("| Alpha | 2025 |", value["candidate_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_before_hidden_verifier"], 1)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertEqual(receipt["hidden_verifier_admitted_cells"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.calls, 1)
        self.assertEqual(search.fetch_calls, 10)

    def test_hidden_conflict_reverts_candidate_without_new_model_call(self) -> None:
        value, model, search = self.run_case(search=Search(verifier_conflict=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_before_hidden_verifier"], 1)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)
        self.assertEqual(receipt["hidden_verifier_reverted_cells"], 1)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.fetch_calls, 10)

    def test_fetch_failure_partition_mismatch_fails_closed(self) -> None:
        value, _, _ = self.run_case(search=Search(verifier_failure=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertFalse(receipt["partition_replay_matches_successful_pages"])
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_hidden_pages_never_enter_parent_prompt_or_parent_pages(self) -> None:
        value, model, _ = self.run_case()
        hidden = value["private_replay_state"]["verifier_pages"]
        prompt_text = "\n".join(user for _, user, _ in model.prompts)
        parent_private = value["parent_result"]["semantic_result"][
            "semantic_active_private_state"
        ]
        parent_pages = [
            *parent_private["raw_core_pages"],
            *parent_private["raw_reserve_pages"],
        ]
        parent_hosts = {page["host"] for page in parent_pages}
        for page in hidden:
            self.assertNotIn(page["host"], parent_hosts)
            self.assertNotIn(page["content"], prompt_text)
        receipt = value["hidden_verifier_receipt"]
        self.assertFalse(
            receipt["hidden_verifier_pages_used_for_candidate_generation_or_model_prompt"]
        )

    def test_partition_occurs_before_candidate_and_is_content_independent(self) -> None:
        first, _, _ = self.run_case()
        second, _, _ = self.run_case(search=Search(verifier_conflict=True))
        a = first["hidden_verifier_receipt"]["partition_receipt"]
        b = second["hidden_verifier_receipt"]["partition_receipt"]
        self.assertEqual(a, b)
        self.assertTrue(a["source_partition_precedes_fetch_and_candidate_discovery"])
        self.assertFalse(
            a["candidate_value_entropy_page_content_or_evaluator_used_for_partition"]
        )
        self.assertFalse(a["verifier_leads_exposed_to_parent_search_or_model_prompt"])

    def test_private_or_public_tamper_fails_replay(self) -> None:
        value, _, _ = self.run_case()
        for field in (
            "private_catalog",
            "private_batch",
            "private_page_cap",
            "public",
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "private_catalog":
                    altered["private_replay_state"]["utility_catalog"][
                        "utility_sets"
                    ][0]["verifier_outcome_delta"] = 0
                elif field == "private_batch":
                    altered["private_replay_state"]["verifier_fetch_batches"][0][
                        "results"
                    ][0]["raw_content"] += " tampered"
                elif field == "private_page_cap":
                    altered["private_replay_state"]["page_character_cap"] = 1
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
            run_v24351_task(
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

    def test_public_receipt_is_content_free_label_blind_and_bounded(self) -> None:
        value, _, _ = self.run_case()
        receipt = value["hidden_verifier_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("Alpha was founded", encoded)
        self.assertNotIn("source3.example", encoded)
        forbidden_raw_keys = {
            "question",
            "query",
            "url",
            "host",
            "content",
            "candidate_value",
            "evidence_id",
        }

        def keys(raw):
            if isinstance(raw, dict):
                return set(raw) | set().union(*(keys(item) for item in raw.values()))
            if isinstance(raw, list):
                return set().union(*(keys(item) for item in raw))
            return set()

        self.assertFalse(keys(receipt) & forbidden_raw_keys)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertLessEqual(receipt["total_fetch_calls"], 10)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
