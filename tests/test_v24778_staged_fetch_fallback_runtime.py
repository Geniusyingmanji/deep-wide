from __future__ import annotations

import ast
import copy
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent import v24778_staged_fetch_fallback_runtime as target  # noqa: E402


ENTITIES = ("Alpha Institute", "Beta Labs", "Gamma College", "Delta Academy")
QUESTION = (
    "Use public web sources to return one Markdown table about these organizations:\n"
    "<ENTITIES>\n"
    + "\n".join(f"{index}. {entity}" for index, entity in enumerate(ENTITIES, 1))
    + "\n</ENTITIES>\n"
    "The column names are: Organization, Founded, Country. "
    "Use a four-digit founding year and the English country name. "
    "Use Unknown unless an exact value is supported by two independent public sources. "
    "Return one table only."
)
TASK = {"opaque_id": "task_1234567890abcdef12345678", "question": QUESTION}
LIMITS = ScoreFirstLimits(
    wall_seconds=60,
    model_calls=2,
    search_queries=4,
    fetch_targets=10,
    search_results_per_query=3,
    evidence_chars=60_000,
    page_chars=5_000,
    plan_output_tokens=4_000,
    synthesis_output_tokens=30_000,
    repair_output_tokens=12_000,
)
BASELINE = (
    "```markdown\n| Organization | Founded | Country |\n"
    "| --- | --- | --- |\n"
    + "\n".join(f"| {entity} | Unknown | Unknown |" for entity in ENTITIES)
    + "\n```"
)


def lead(entity: str, source: str, *, suffix: str = "record") -> dict[str, str]:
    return {
        "title": f"{entity} institutional profile",
        "url": f"https://{source}/{suffix}",
        "fetch_url": f"https://{source}/{suffix}",
    }


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
            return ModelResult(
                json.dumps(
                    {
                        "language": "English",
                        "columns": ["Organization", "Founded", "Country"],
                        "row_target_hint": "4",
                        "queries": ["one", "two", "three", "four"],
                    }
                ),
                {},
                None,
                1,
            )
        return ModelResult(BASELINE, {}, None, 1)


class Search:
    def __init__(
        self,
        values: list[dict[str, str]],
        contents: dict[str, str],
        failures: set[str] | None = None,
        raise_on_fetch_batch: int | None = None,
    ) -> None:
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
        self.values = values
        self.contents = contents
        self.failed = set(failures or ())
        self.raise_on_fetch_batch = raise_on_fetch_batch
        self.seen_queries: list[str] = []
        self.fetch_batches: list[list[str]] = []

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.seen_queries = list(queries)
        return [
            {
                "query": "provider union",
                "answer": "discarded",
                "results": copy.deepcopy(self.values),
                "error": None,
            }
        ]

    def fetch_urls(self, requests):
        urls = [request["url"] for request in requests]
        self.fetch_batches.append(urls)
        if len(self.fetch_batches) == self.raise_on_fetch_batch:
            raise RuntimeError("synthetic fetch batch failure")
        self.fetch_calls += len(urls)
        output = []
        for request in requests:
            url = request["url"]
            if url in self.failed:
                self.fetch_failures += 1
                output.append(
                    {
                        "query": request.get("query", ""),
                        "answer": "",
                        "results": [],
                        "error": "http_503",
                    }
                )
                continue
            output.append(
                {
                    "query": request.get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": request.get("title", ""),
                            "url": url,
                            "fetch_url": url,
                            "requested_url": url,
                            "content": "",
                            "raw_content": self.contents[url],
                            "fetch_status": "ok",
                        }
                    ],
                    "error": None,
                }
            )
        return output


def two_round_values() -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for round_index in range(1, 4):
        for entity_index, entity in enumerate(ENTITIES):
            values.append(
                lead(entity, f"e{entity_index + 1}r{round_index}.example")
            )
    return values


class V24778StagedFetchFallbackRuntimeTests(unittest.TestCase):
    def test_reserve_targets_lowest_coverage_with_new_sources(self) -> None:
        values = two_round_values()
        initial, _ = target.semantic.select_visible_entity_fair_leads(
            values, entities=ENTITIES, limit=10
        )
        reserve, diagnostic = target.select_staged_reserve_leads(
            values,
            entities=ENTITIES,
            initial_requests=initial[:8],
            initial_identity_sources=[[], ["a.example"], ["b.example", "c.example"], ["d.example", "e.example"]],
        )
        self.assertEqual(len(reserve), 2)
        self.assertEqual(diagnostic["reserve_request_alignment_count_vector"], [1, 1, 0, 0])
        initial_sources = {target.semantic._lead_source(item) for item in initial[:8]}
        self.assertTrue(
            {target.semantic._lead_source(item) for item in reserve}.isdisjoint(
                initial_sources
            )
        )

    def test_second_reserve_is_not_wasted_on_already_covered_entity(self) -> None:
        initial = [
            lead(ENTITIES[0], "a-initial.example"),
            lead(ENTITIES[1], "b-initial.example"),
            lead(ENTITIES[2], "c-initial.example"),
            lead(ENTITIES[3], "d-initial.example"),
        ]
        values = [
            *initial,
            lead(ENTITIES[0], "a-reserve-one.example"),
            lead(ENTITIES[0], "a-reserve-two.example"),
            lead(ENTITIES[2], "c-reserve.example"),
        ]
        reserve, diagnostic = target.select_staged_reserve_leads(
            values,
            entities=ENTITIES,
            initial_requests=initial,
            initial_identity_sources=[[], ["b.example"], ["c1.example", "c2.example"], ["d1.example", "d2.example"]],
        )
        self.assertEqual(len(reserve), 2)
        self.assertEqual(diagnostic["reserve_request_alignment_count_vector"], [2, 0, 0, 0])

    def test_failed_initial_urls_are_not_retried_and_total_targets_stay_ten(self) -> None:
        values = two_round_values()
        contents = {
            item["url"]: f"{item['title']}. No explicit founding relation."
            for item in values
        }
        provisional, _ = target.semantic.select_visible_entity_fair_leads(
            values, entities=ENTITIES, limit=10
        )
        failed = {provisional[0]["fetch_url"], provisional[1]["fetch_url"]}
        search = Search(values, contents, failures=failed)
        result = target.run_v24778_task(
            TASK, model=Model(), search=search, limits=LIMITS, monotonic=time.monotonic
        )
        self.assertEqual(target.validate_result(result), result)
        self.assertEqual([len(batch) for batch in search.fetch_batches], [8, 2])
        flattened = [url for batch in search.fetch_batches for url in batch]
        self.assertEqual(len(flattened), 10)
        self.assertEqual(len(set(flattened)), 10)
        self.assertTrue(failed.issubset(set(search.fetch_batches[0])))
        self.assertTrue(failed.isdisjoint(set(search.fetch_batches[1])))
        receipt = result["scheduler_receipt"]
        self.assertEqual(receipt["failed_url_retry_count"], 0)
        self.assertEqual(receipt["actual_fetch_request_count"], 10)
        self.assertEqual(receipt["initial_usable_page_count"], 6)
        self.assertEqual(receipt["reserve_usable_page_count"], 2)
        self.assertFalse(
            receipt[
                "field_label_candidate_value_or_model_judgment_used_for_reserve_routing"
            ]
        )

    def test_success_identity_coverage_routes_reserve_without_field_values(self) -> None:
        values = two_round_values()
        contents = {}
        for item in values:
            contents[item["url"]] = item["title"] + ". Generic profile text."
        provisional, _ = target.semantic.select_visible_entity_fair_leads(
            values, entities=ENTITIES, limit=10
        )
        failed = {
            provisional[0]["fetch_url"],
            provisional[4]["fetch_url"],
        }
        search = Search(values, contents, failures=failed)
        result = target.run_v24778_task(
            TASK, model=Model(), search=search, limits=LIMITS, monotonic=time.monotonic
        )
        receipt = result["scheduler_receipt"]
        self.assertEqual(receipt["reserve_fetch_request_count"], 2)
        self.assertGreaterEqual(receipt["reserve_target_entity_count"], 1)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(result["semantic_receipt"]["final_changed_cell_count"], 0)

    def test_initial_fetch_exception_stops_reserve_fail_closed(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        search = Search(values, contents, raise_on_fetch_batch=1)
        result = target.run_v24778_task(
            TASK, model=Model(), search=search, limits=LIMITS, monotonic=time.monotonic
        )
        receipt = result["scheduler_receipt"]
        self.assertEqual([len(batch) for batch in search.fetch_batches], [8])
        self.assertEqual(receipt["initial_fetch_exception_count"], 1)
        self.assertEqual(receipt["reserve_fetch_request_count"], 0)
        self.assertEqual(receipt["actual_fetch_request_count"], 8)
        self.assertEqual(receipt["actual_usable_page_count"], 0)
        self.assertEqual(
            result["predictions"]["staged_fallback_semantic"],
            result["predictions"]["baseline"],
        )

    def test_multi_entity_aligned_reserve_has_one_assignment_owner(self) -> None:
        values = two_round_values()
        shared = {
            "title": f"{ENTITIES[0]} and {ENTITIES[1]} institutional profiles",
            "url": "https://shared-reserve.example/record",
            "fetch_url": "https://shared-reserve.example/record",
        }
        values.append(shared)
        initial, _ = target.semantic.select_visible_entity_fair_leads(
            values, entities=ENTITIES, limit=10
        )
        reserve, diagnostic = target.select_staged_reserve_leads(
            values,
            entities=ENTITIES,
            initial_requests=initial[:8],
            initial_identity_sources=[[], [], ["g.example"], ["d.example"]],
        )
        self.assertEqual(len(reserve), 2)
        self.assertEqual(
            sum(diagnostic["reserve_request_alignment_count_vector"]), len(reserve)
        )

    def test_redirect_final_host_controls_identity_source_independence(self) -> None:
        requests = [lead(ENTITIES[0], "requested.example")]
        batches = [
            {
                "results": [
                    {
                        "requested_url": requests[0]["url"],
                        "fetch_url": requests[0]["url"],
                        "url": "https://final.example/profile",
                        "raw_content": f"{ENTITIES[0]} profile",
                    }
                ]
            }
        ]
        target._validate_fetched_batches(batches, requests=requests)
        replay = [
            {
                "final_url": "https://final.example/profile",
                "content": f"{ENTITIES[0]} profile",
                "fetch_integrity": True,
            }
        ]
        sources = target._identity_sources_from_replay(replay, ENTITIES)
        self.assertEqual(sources[0], ["final.example"])
        candidate = lead(ENTITIES[0], "final.example", suffix="other")
        reserve, _ = target.select_staged_reserve_leads(
            [*requests, candidate],
            entities=ENTITIES,
            initial_requests=requests,
            initial_identity_sources=sources,
        )
        self.assertEqual(reserve, [])

    def test_unbound_fetch_result_is_rejected(self) -> None:
        requests = [lead(ENTITIES[0], "requested.example")]
        batches = [
            {
                "results": [
                    {
                        "url": "https://requested.example/profile",
                        "raw_content": f"{ENTITIES[0]} profile",
                    }
                ]
            }
        ]
        with self.assertRaises(ValueError):
            target._validate_fetched_batches(batches, requests=requests)

    def test_two_source_semantic_gate_is_unchanged(self) -> None:
        values = two_round_values()
        contents = {}
        for item in values:
            contents[item["url"]] = (
                f"{ENTITIES[0]} was founded in 1999."
                if item["title"].startswith(ENTITIES[0])
                else item["title"] + ". Generic profile text."
            )
        result = target.run_v24778_task(
            TASK,
            model=Model(),
            search=Search(values, contents),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        self.assertIn(
            "| Alpha Institute | 1999 | Unknown |",
            result["predictions"]["staged_fallback_semantic"],
        )
        self.assertGreaterEqual(
            result["semantic_receipt"]["projection_backed_eligible_support_set_count"],
            1,
        )
        self.assertFalse(
            result["scheduler_receipt"]["strict_two_independent_same_value_gate_changed"]
        )

    def test_no_reserve_candidate_uses_fewer_than_ten_without_unaligned_fill(self) -> None:
        values = [lead(entity, f"source{index}.example") for index, entity in enumerate(ENTITIES)]
        contents = {item["url"]: item["title"] for item in values}
        search = Search(values, contents)
        result = target.run_v24778_task(
            TASK, model=Model(), search=search, limits=LIMITS, monotonic=time.monotonic
        )
        self.assertEqual([len(batch) for batch in search.fetch_batches], [4])
        self.assertEqual(result["scheduler_receipt"]["reserve_fetch_request_count"], 0)
        self.assertEqual(result["scheduler_receipt"]["actual_fetch_request_count"], 4)

    def test_parent_authorized_nine_targets_cannot_expand_to_ten(self) -> None:
        values = two_round_values()[:9]
        contents = {item["url"]: item["title"] for item in values}
        search = Search(values, contents)
        result = target.run_v24778_task(
            TASK, model=Model(), search=search, limits=LIMITS, monotonic=time.monotonic
        )
        self.assertEqual([len(batch) for batch in search.fetch_batches], [8, 1])
        receipt = result["scheduler_receipt"]
        self.assertEqual(receipt["provisional_fetch_lead_count"], 9)
        self.assertEqual(receipt["actual_fetch_request_count"], 9)
        self.assertEqual(search.fetch_calls, 9)

    def test_result_and_private_coverage_tamper_fail_closed(self) -> None:
        values = two_round_values()
        contents = {item["url"]: item["title"] for item in values}
        result = target.run_v24778_task(
            TASK,
            model=Model(),
            search=Search(values, contents),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        altered = copy.deepcopy(result)
        altered["private_scheduler_state"]["initial_identity_sources"][0] = []
        altered["scheduler_receipt"] = target._scheduler_receipt(
            altered["private_scheduler_state"]
        )
        altered["result_sha256"] = target.payload_sha256(
            {key: value for key, value in altered.items() if key != "result_sha256"}
        )
        with self.assertRaises(ValueError):
            target.validate_result(altered)

    def test_runtime_is_label_blind_and_has_no_evaluator_or_external_import(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        privileged = {
            "answer_key",
            "benchmark_question_type",
            "category",
            "evaluator",
            "gold",
            "ground_truth",
            "mapping",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        external = {"httpx", "requests", "socket", "subprocess"}
        findings = []
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key.casefold() in privileged:
                findings.append((node.lineno, key))
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            findings.extend((node.lineno, name) for name in names if name in external)
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
