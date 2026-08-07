from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent import v24756_zero_effect_structured_integration as target  # noqa: E402


QUESTION = (
    "Use public web sources to return one Markdown table. "
    "The column names are: Organization, Founded, Country. Return one table only."
)
TASK = {"opaque_id": "task_1234567890abcdef12345678", "question": QUESTION}
LIMITS = {
    "wall_seconds": 60,
    "model_calls": 2,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
BASELINE = """```markdown
| Organization | Founded | Country |
| --- | --- | --- |
| Alpha Institute | Unknown | Existing |
| Beta Labs | Unknown | Unknown |
```"""
STRUCTURED = """| Organization | Founded | Country |
| --- | --- | --- |
| Alpha Institute | 1999 | Changed |
| Beta Labs | 2001 | Canada |"""


class Model:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if json_mode:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["Organization", "Founded", "Country"],
                    "row_target_hint": "2",
                    "queries": ["organizations founded country"],
                }
            )
        else:
            text = BASELINE
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self, *, hosts=("one.example", "two.example.net")) -> None:
        for name in (
            "calls",
            "failures",
            "tool_calls",
            "fetch_calls",
            "fetch_failures",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        ):
            setattr(self, name, 0)
        self.hosts = hosts

    def search_many(self, queries, **kwargs):
        self.calls += 1
        return [
            {
                "query": "q",
                "answer": "",
                "results": [
                    {
                        "title": "records",
                        "url": f"https://{host}/requested",
                        "fetch_url": f"https://{host}/requested",
                        "content": "",
                        "raw_content": "",
                    }
                    for host in self.hosts
                ],
                "error": None,
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_calls += len(requests)
        return [
            {
                "query": request.get("query", "q"),
                "answer": "",
                "results": [
                    {
                        "title": "records",
                        "url": request["url"].replace("/requested", "/final"),
                        "fetch_url": request["url"],
                        "requested_url": request["url"],
                        "content": "",
                        "raw_content": STRUCTURED,
                        "fetch_status": "ok",
                    }
                ],
                "error": None,
            }
            for request in requests
        ]


class V24756ZeroEffectStructuredIntegrationTests(unittest.TestCase):
    def test_candidate_replays_same_pages_without_new_effect(self) -> None:
        model = Model()
        search = Search()
        result = target.run_v24756_task(
            TASK,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**LIMITS),
        )
        self.assertEqual(target.validate_result(result), result)
        self.assertIn(
            "| Alpha Institute | 1999 | Existing |",
            result["predictions"]["generic_structured"],
        )
        self.assertIn(
            "| Beta Labs | 2001 | Canada |",
            result["predictions"]["generic_structured"],
        )
        receipt = result["receipt"]
        self.assertTrue(receipt["adapter_effect_equivalence_passed"])
        self.assertFalse(receipt["candidate_additional_query_fetch_or_model_effect"])
        self.assertEqual(model.requests, 2)
        self.assertEqual(receipt["adapter_additional_model_requests"], 0)
        self.assertEqual(receipt["adapter_additional_fetch_calls"], 0)
        self.assertEqual(receipt["adapter_replay_page_count"], 2)
        self.assertTrue(receipt["adapter_pages_are_subset_of_synthesis_evidence"])
        self.assertTrue(
            all(page["final_url"].endswith("/final") for page in result["private_replay_pages"])
        )

    def test_same_registrable_source_abstains(self) -> None:
        result = target.run_v24756_task(
            TASK,
            model=Model(),
            search=Search(hosts=("one.example.org", "two.example.org")),
            limits=ScoreFirstLimits(**LIMITS),
        )
        self.assertEqual(
            result["predictions"]["generic_structured"],
            result["predictions"]["baseline"],
        )
        self.assertGreater(
            result["receipt"]["adapter_content_free_receipt"][
                "binding_receipt"
            ]["insufficient_corroboration_cell_count"],
            0,
        )

    def test_replay_requires_all_fetched_page_content_to_fit_synthesis_cap(self) -> None:
        limits = dict(LIMITS)
        limits["evidence_chars"] = 49_999
        with self.assertRaises(ValueError):
            target.run_v24756_task(
                TASK,
                model=Model(),
                search=Search(),
                limits=ScoreFirstLimits(**limits),
            )

    def test_nonfetched_snippet_or_missing_final_status_is_not_replayed(self) -> None:
        batches = [
            {
                "results": [
                    {
                        "url": "https://one.example/final",
                        "raw_content": STRUCTURED,
                        "content": "snippet",
                        "fetch_status": "not_attempted",
                    },
                    {
                        "url": "https://two.example.net/final",
                        "raw_content": "",
                        "content": STRUCTURED,
                        "fetch_status": "ok",
                    },
                ]
            }
        ]
        self.assertEqual(target._adapter_pages(batches, page_chars=5_000), [])

    def test_result_tamper_and_effect_counter_drift_fail(self) -> None:
        result = target.run_v24756_task(
            TASK,
            model=Model(),
            search=Search(),
            limits=ScoreFirstLimits(**LIMITS),
        )
        altered = copy.deepcopy(result)
        altered["receipt"]["model_cost_after_adapter"]["requests"] += 1
        altered["receipt"].pop("receipt_sha256")
        altered["receipt"]["receipt_sha256"] = target.payload_sha256(
            altered["receipt"]
        )
        altered.pop("result_sha256")
        altered["result_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_result(altered)
        foreign = copy.deepcopy(result)
        foreign["private_replay_pages"][0]["content"] = "foreign content"
        foreign.pop("result_sha256")
        foreign["result_sha256"] = target.payload_sha256(foreign)
        with self.assertRaises(ValueError):
            target.validate_result(foreign)
        summary = copy.deepcopy(result)
        summary["receipt"]["candidate_table"]["unknown_value_cell_count"] += 1
        summary["receipt"].pop("receipt_sha256")
        summary["receipt"]["receipt_sha256"] = target.payload_sha256(
            summary["receipt"]
        )
        summary.pop("result_sha256")
        summary["result_sha256"] = target.payload_sha256(summary)
        with self.assertRaises(ValueError):
            target.validate_result(summary)

    def test_runtime_has_no_privileged_or_evaluator_access(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        privileged = {
            "answer",
            "answer_key",
            "category",
            "evaluator",
            "gold",
            "ground_truth",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        accesses = []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if str(node.slice.value).casefold() in privileged:
                    accesses.append(node.lineno)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        self.assertEqual(accesses, [])
        self.assertFalse(any("evaluator" in name.casefold() for name in imports))


if __name__ == "__main__":
    unittest.main()
