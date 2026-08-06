from __future__ import annotations

import ast
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits
from deepwide_agent.v24648_unknown_target_structured_runtime import (
    exact_lookup_url,
    project_exact_lookup_pages,
    run_v24648_task,
    unknown_target_lookup_requests,
    validate_result,
)


ENTITIES = (
    "Alpha Research Institute",
    "Beta Foundation",
    "Gamma Laboratory",
    "Delta Centre",
)
SUFFIXES = ("01abc2d34", "02abc3d45", "03abc4d56", "04abc5d67")


def table(rows: list[list[str]]) -> str:
    return (
        "```markdown\n| Organization | ROR ID | Country code |\n"
        "| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def baseline() -> str:
    return table(
        [
            [ENTITIES[0], "Unknown", "FR"],
            [ENTITIES[1], "099999999", "US"],
            [ENTITIES[2], "Unknown", "DE"],
            [ENTITIES[3], "Unknown", "AU"],
        ]
    )


def visible_task() -> dict[str, str]:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(ENTITIES, 1))
    return {
        "opaque_id": "task_000000000000000000246480",
        "question": (
            "Use public web sources to return one Markdown table about these organizations:\n"
            f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
            "The column names are: Organization, ROR ID, Country code. "
            "Use the 9-character ROR ID suffix, not the full URL, and the ISO 3166-1 alpha-2 country code. "
            "Return one table only."
        ),
    }


def lookup_response(entity: str, suffixes: list[str]) -> str:
    return json.dumps(
        {
            "number_of_results": len(suffixes),
            "items": [
                {
                    "id": f"https://ror.org/{suffix}",
                    "status": "active",
                    "names": [{"value": entity, "types": ["ror_display"]}],
                }
                for suffix in suffixes
            ],
        }
    )


class Model:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        text = (
            json.dumps(
                {
                    "language": "English",
                    "columns": ["Organization", "ROR ID", "Country code"],
                    "row_target_hint": "4",
                    "queries": ["ignored"],
                }
            )
            if self.requests == 1
            else baseline()
        )
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self) -> None:
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
        self.queries: list[str] = []
        self.fetch_vectors: list[list[dict[str, str]]] = []

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.queries = list(queries)
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "title": f"generic-{index}",
                        "url": f"https://example.org/page-{query_index}-{index}",
                        "fetch_url": f"https://example.org/page-{query_index}-{index}",
                    }
                    for index in range(3)
                ],
                "error": None,
            }
            for query_index, query in enumerate(queries)
        ]

    def fetch_urls(self, requests):
        self.fetch_calls += 1
        values = list(requests)
        self.fetch_vectors.append(values)
        if values and "api.ror.org" in values[0]["url"]:
            return [
                {
                    "query": request["query"],
                    "answer": "",
                    "results": [
                        {
                            "title": "",
                            "url": request["url"],
                            "raw_content": lookup_response(
                                request["member_label"],
                                [SUFFIXES[ENTITIES.index(request["member_label"])]],
                            ),
                            "directory_member_label": request["member_label"],
                        }
                    ],
                    "error": None,
                }
                for request in values
            ]
        return [
            {
                "query": request["query"],
                "answer": "",
                "results": [
                    {
                        "title": "unrelated page",
                        "url": request["url"],
                        "raw_content": "generic evidence",
                    }
                ],
                "error": None,
            }
            for request in values
        ]


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )


class LookupTests(unittest.TestCase):
    def test_requests_only_unknown_rows_and_are_exact_official_urls(self) -> None:
        requests = unknown_target_lookup_requests(baseline(), ENTITIES)
        self.assertEqual(
            [request["member_label"] for request in requests],
            [ENTITIES[0], ENTITIES[2], ENTITIES[3]],
        )
        self.assertEqual(
            [request["url"] for request in requests],
            [exact_lookup_url(entity) for entity in (ENTITIES[0], ENTITIES[2], ENTITIES[3])],
        )

    def test_unique_exact_active_display_is_projected(self) -> None:
        entity = ENTITIES[0]
        batches = [
            {
                "results": [
                    {
                        "url": exact_lookup_url(entity),
                        "raw_content": lookup_response(entity, [SUFFIXES[0]]),
                    }
                ]
            }
        ]
        pages, stats = project_exact_lookup_pages(batches, [entity])
        self.assertEqual(len(pages), 1)
        self.assertEqual(stats["unique_exact_response_count"], 1)
        self.assertEqual(pages[0]["url"], f"https://api.ror.org/v2/organizations/{SUFFIXES[0]}")

    def test_ambiguous_query_literal_is_rejected_before_effect(self) -> None:
        for entity in ('Quoted "Institute"', "Backslash \\ Institute"):
            with self.assertRaisesRegex(ValueError, "lookup target drifted"):
                exact_lookup_url(entity)

    def test_ambiguous_mismatch_truncation_and_url_tamper_fail_closed(self) -> None:
        entity = ENTITIES[0]
        cases = (
            (exact_lookup_url(entity), lookup_response(entity, [SUFFIXES[0], SUFFIXES[1]])),
            (exact_lookup_url(entity), lookup_response("Different Organization", [SUFFIXES[0]])),
            (exact_lookup_url(entity), '{"number_of_results":1,"items":['),
            ("https://example.org/v2/organizations", lookup_response(entity, [SUFFIXES[0]])),
            (
                exact_lookup_url(entity),
                json.dumps(
                    {
                        "number_of_results": 2,
                        "items": json.loads(
                            lookup_response(entity, [SUFFIXES[0]])
                        )["items"],
                    }
                ),
            ),
        )
        expected_pages = (2, 0, 0, 0, 0)
        for (url, content), amount in zip(cases, expected_pages, strict=True):
            pages, _stats = project_exact_lookup_pages(
                [{"results": [{"url": url, "raw_content": content}]}], [entity]
            )
            self.assertEqual(len(pages), amount)


class RuntimeTests(unittest.TestCase):
    def test_two_model_four_query_and_ten_fetch_cap_with_safe_fill(self) -> None:
        model = Model()
        search = Search()
        result = run_v24648_task(
            visible_task(), model=model, search=search, limits=limits(), monotonic=time.monotonic
        )
        validate_result(result)
        receipt = result["receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(len(search.queries), 4)
        self.assertEqual([len(vector) for vector in search.fetch_vectors], [6, 3])
        self.assertEqual(receipt["admitted_total_fetch_targets"], 9)
        self.assertEqual(receipt["generic_fetch_targets"], 6)
        self.assertEqual(receipt["unknown_target_lookup_fetch_targets"], 3)
        self.assertEqual(receipt["discovery"]["admitted_replacement_count"], 3)
        candidate = result["predictions"]["unknown_target_structured"]
        self.assertIn(f"| {ENTITIES[0]} | {SUFFIXES[0]} | FR |", candidate)
        self.assertIn(f"| {ENTITIES[1]} | 099999999 | US |", candidate)
        self.assertIn(f"| {ENTITIES[2]} | {SUFFIXES[2]} | DE |", candidate)
        self.assertIn(f"| {ENTITIES[3]} | {SUFFIXES[3]} | AU |", candidate)
        self.assertFalse(receipt["positive_task_credit_assigned"])

    def test_runtime_source_has_no_privileged_or_io_capability(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v24648_unknown_target_structured_runtime.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                name.split(".")[0]
                in {"pathlib", "os", "subprocess", "socket", "urllib.request"}
                for name in imports
            )
        )
        for marker in ("evaluation/", "ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(marker, source)
        privileged_fields = {
            "question_type",
            "benchmark_question_type",
            "task_category",
            "category",
            "split",
            "mapping",
            "gold",
            "score",
            "reward",
        }
        reads = {
            node.slice.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
            and isinstance(node.ctx, ast.Load)
        }
        self.assertFalse(reads & privileged_fields)


if __name__ == "__main__":
    unittest.main()
