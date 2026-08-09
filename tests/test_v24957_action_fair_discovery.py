from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24957_action_fair_discovery as target  # noqa: E402


def source(label: str) -> dict[str, str]:
    return {
        "type": "url",
        "title": "",
        "url": f"https://{label}.example/record",
        "fetch_url": f"https://{label}.example/record",
    }


def batches() -> list[dict]:
    return [
        {
            "query": "discarded task-local query",
            "answer": "discarded",
            "results": [source("local")],
            "error": None,
            "hosted_search_trace": {
                "actions": [
                    {"sources": [source(f"a{index}") for index in range(1, 6)]},
                    {"sources": [source("b1"), source("b2")]},
                    {"sources": [source("c1")]},
                ]
            },
        }
    ]


class Inner:
    def __init__(self) -> None:
        for name in target.COUNTERS:
            setattr(self, name, 0)

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.tool_calls += 3
        return copy.deepcopy(batches())

    def fetch_urls(self, requests):
        self.fetch_calls += len(requests)
        return []


class V24957ActionFairDiscoveryTests(unittest.TestCase):
    def test_pure_order_preserves_source_set_and_round_robins_actions(self) -> None:
        fair, observation, memberships = target.order_action_fair_leads(batches())
        labels = [item["url"].split("//", 1)[1].split(".", 1)[0] for item in fair]
        self.assertEqual(labels[:7], ["local", "a1", "b1", "c1", "a2", "b2", "a3"])
        self.assertEqual(set(labels), {"local", "a1", "a2", "a3", "a4", "a5", "b1", "b2", "c1"})
        self.assertEqual(observation["raw_action_group_count"], 3)
        self.assertEqual(observation["action_groups_with_ordered_lead_count"], 3)
        self.assertEqual(memberships["https://b1.example/record"], frozenset({1}))

    def test_budget_prefix_improves_group_coverage_without_more_sources(self) -> None:
        client = target.ActionFairBudgetEquivalentTaskUnionSearchClient(
            Inner(), search_results_per_query=3, global_fetch_cap=4
        )
        result = client.search_many(["q1", "q2"], max_results=3)
        labels = [
            item["url"].split("//", 1)[1].split(".", 1)[0]
            for item in result[0]["results"]
        ]
        self.assertEqual(labels, ["local", "a1", "b1", "c1"])
        receipt = client.action_fair_budget_receipt()
        self.assertEqual(receipt["post_cap_source_count"], 4)
        self.assertEqual(receipt["stable_prefix_action_group_count"], 1)
        self.assertEqual(receipt["fair_prefix_action_group_count"], 3)
        self.assertEqual(receipt["action_group_coverage_gain"], 2)
        self.assertEqual(receipt["selection_changed_invocation_count"], 1)
        self.assertEqual(client.receipt(), receipt)
        self.assertEqual(client.parent.receipt()["union_source_count"], 9)
        self.assertEqual(
            client.parent.action_fair_receipt()["raw_action_source_count"], 8
        )

    def test_successor_receipt_does_not_mislabel_order_as_stable_first_seen(self) -> None:
        client = target.ActionFairBudgetEquivalentTaskUnionSearchClient(
            Inner(), search_results_per_query=3, global_fetch_cap=4
        )
        client.search_many(["q1", "q2"], max_results=3)
        receipt = client.receipt()
        self.assertEqual(receipt["ordering_policy"], target.ORDERING_POLICY)
        self.assertNotIn("selection_policy", receipt)
        self.assertNotIn("parent_discovery_receipt_sha256", receipt)

    def test_duplicate_url_across_groups_is_emitted_once_and_credits_membership(self) -> None:
        raw = batches()
        shared = source("shared")
        raw[0]["hosted_search_trace"]["actions"] = [
            {"sources": [shared, source("a")]},
            {"sources": [shared, source("b")]},
        ]
        fair, observation, memberships = target.order_action_fair_leads(raw)
        urls = [item["url"] for item in fair]
        self.assertEqual(urls.count("https://shared.example/record"), 1)
        self.assertEqual(
            memberships["https://shared.example/record"], frozenset({0, 1})
        )
        self.assertEqual(observation["duplicate_source_count"], 1)

    def test_empty_or_failed_input_is_total_and_content_free(self) -> None:
        fair, observation, memberships = target.order_action_fair_leads([])
        self.assertEqual(fair, [])
        self.assertEqual(memberships, {})
        self.assertEqual(observation["raw_action_group_count"], 0)
        client = target.ActionFairBudgetEquivalentTaskUnionSearchClient(
            Inner(), search_results_per_query=3, global_fetch_cap=10
        )
        client.parent.inner.search_many = lambda *_args, **_kwargs: []
        self.assertEqual(client.search_many(["q"], max_results=3), [])
        self.assertEqual(client.action_fair_budget_receipt()["post_cap_source_count"], 0)

    def test_source_has_no_evaluator_or_privileged_runtime_capability(self) -> None:
        source_text = (
            ROOT / "src/deepwide_agent/v24957_action_fair_discovery.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        self.assertNotIn("os.environ", source_text)
        for forbidden in ("answer_key", "ground_truth", "benchmark_question_type"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
