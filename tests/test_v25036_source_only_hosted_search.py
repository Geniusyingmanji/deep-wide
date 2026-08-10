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

from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
)
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    validate_receipt as validate_single_shot_receipt,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    RobustLatePageBoundSearchClient,
)
from deepwide_agent.v25036_source_only_hosted_search import (  # noqa: E402
    SOURCE_ONLY_MAX_OUTPUT_TOKENS,
    SourceOnlyRobustLatePageBoundSearchClient,
    build_source_only_request_body,
    validate_search_class,
    validate_source_only_request_body,
)


QUERIES = ["Alpha official list", "Alpha public database"]


def payload() -> dict:
    return {
        "id": "response",
        "output": [
            {
                "type": "web_search_call",
                "id": "call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": list(QUERIES),
                    "sources": [
                        {
                            "type": "web_source",
                            "url": "https://a.example/page",
                            "title": "A",
                        },
                        {
                            "type": "web_source",
                            "url": "https://b.example/page",
                            "title": "B",
                        },
                    ],
                },
            },
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "done", "annotations": []}],
            },
        ],
    }


class FakeSourceOnly(SourceOnlyRobustLatePageBoundSearchClient):
    def __init__(self, response: dict) -> None:
        # Avoid the production helper identity check in this pure parser test;
        # initialize the inherited native counters directly through the next
        # concrete class after the robust late-page wrapper.
        from deepwide_agent.v24630_thin_backfill_search import (
            ThinSameResponseCitationTitleBackfillSearchClient,
        )

        ThinSameResponseCitationTitleBackfillSearchClient.__init__(
            self,
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            batch_size=8,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=10_000_000_000.0,
        )
        self.response = copy.deepcopy(response)
        self.requests: list[list[str]] = []

    def _request(self, queries):  # type: ignore[override]
        self.requests.append(list(queries))
        return copy.deepcopy(self.response)


class SourceOnlyHostedSearchTests(unittest.TestCase):
    def test_request_keeps_queries_tool_sources_and_fixed_cap(self) -> None:
        body = build_source_only_request_body(
            model="gpt-5.6-sol",
            queries=QUERIES,
            search_context_size="medium",
            reasoning_effort="low",
            service_tier="priority",
        )
        validate_source_only_request_body(body, expected_queries=QUERIES)
        self.assertEqual(body["max_output_tokens"], SOURCE_ONLY_MAX_OUTPUT_TOKENS)
        self.assertEqual(body["include"], ["web_search_call.action.sources"])
        serialized = str(body).casefold()
        self.assertIn("return only the word done", serialized)
        self.assertNotIn("700 characters", serialized)
        self.assertNotIn("evidence summary", serialized)

    def test_invalid_or_duplicate_queries_fail_before_effect(self) -> None:
        for queries in ([], ["same", "same"], [""], ["x" * 2_001]):
            with self.subTest(queries=queries):
                with self.assertRaises(ValueError):
                    build_source_only_request_body(
                        model="gpt-5.6-sol",
                        queries=queries,
                        search_context_size="medium",
                        reasoning_effort="low",
                        service_tier="priority",
                    )

    def test_incomplete_markers_still_recover_action_sources_once(self) -> None:
        inner = FakeSourceOnly(payload())
        union = TaskUnionDiscoverySearchClient(inner)
        batches = union.search_many(QUERIES, max_results=3)
        self.assertEqual(inner.requests, [QUERIES])
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]["results"]), 2)
        self.assertEqual(union.failures, 0)
        discovery = union.receipt()
        self.assertEqual(discovery["raw_action_source_count"], 2)
        self.assertEqual(discovery["union_source_count"], 2)
        self.assertEqual(discovery["raw_query_local_mapping_failure_count"], 2)
        receipt = inner.single_shot_receipt()
        validate_single_shot_receipt(receipt)
        self.assertEqual(receipt["recursive_split_requests"], 0)
        self.assertEqual(receipt["action_trace_attachments"], 1)

    def test_candidate_is_subclass_of_production_search_chain(self) -> None:
        validate_search_class()
        self.assertTrue(
            issubclass(
                SourceOnlyRobustLatePageBoundSearchClient,
                RobustLatePageBoundSearchClient,
            )
        )

    def test_module_has_no_privileged_evaluator_or_direct_effect_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25036_source_only_hosted_search.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "deepwidebench",
            "eval",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        accesses: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    accesses.add(node.slice.value.casefold())
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                accesses.add(node.args[0].value.casefold())
        self.assertFalse(
            accesses
            & {
                "category",
                "question_type",
                "split",
                "mapping",
                "gold",
                "ground_truth",
                "answer_key",
                "evaluator",
                "score",
                "reward",
            }
        )


if __name__ == "__main__":
    unittest.main()
