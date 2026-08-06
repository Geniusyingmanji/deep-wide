from __future__ import annotations

import ast
import copy
import hashlib
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
from deepwide_agent.v24655_unknown_cell_targeted_runtime import (
    _gate_unknown_candidate,
    _independent_pages,
    _selected_leads,
    run_v24655_task,
    unknown_cell_targets,
    validate_result,
)


TASK = {
    "opaque_id": "task_000000000000000000246550",
    "question": (
        "Use public web sources and return one Markdown table. "
        "The column names are: Product, Release Date, Maker. "
        "Return one table only."
    ),
}


def payload_sha256(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def reseal(value) -> None:
    receipt = value["receipt"]
    for admission in receipt["cell_admissions"]:
        support = admission["support_receipt"]
        support.pop("support_receipt_sha256", None)
        support["support_receipt_sha256"] = payload_sha256(support)
    receipt.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = payload_sha256(receipt)
    value.pop("result_sha256", None)
    value["result_sha256"] = payload_sha256(value)


def table(alpha_date: str = "Unknown", beta_maker: str = "Beta Co") -> str:
    return (
        "```markdown\n"
        "| Product | Release Date | Maker |\n"
        "| --- | --- | --- |\n"
        f"| Alpha Phone | {alpha_date} | Acme |\n"
        f"| Beta Phone | 2020 | {beta_maker} |\n"
        "```"
    )


def revision(*, alpha_date: str = "2024-09-20", beta_maker: str = "Beta Co") -> str:
    return json.dumps(
        {
            "candidate_table": table(alpha_date, beta_maker),
            "cell_evidence": [
                {
                    "row_key": "Alpha Phone",
                    "column": "Release Date",
                    "evidence_ids": ["R0001", "R0002"],
                }
            ],
        }
    )


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


class Model:
    def __init__(self, values=None) -> None:
        self.values = list(
            values
            or [
                json.dumps(
                    {
                        "language": "English",
                        "columns": ["wrong"],
                        "row_target_hint": "two products",
                        "queries": ["generic product history", "official releases"],
                    }
                ),
                table(),
                revision(),
            ]
        )
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return ModelResult(value, {}, None, 1)


class Search:
    def __init__(self, *, targeted_sources: int = 4) -> None:
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
        self.targeted_sources = targeted_sources
        self.search_vectors: list[list[str]] = []
        self.fetch_vectors: list[list[dict[str, str]]] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += 1
        self.search_vectors.append(values)
        targeted = len(self.search_vectors) > 1
        count = self.targeted_sources if targeted else 6
        prefix = "target" if targeted else "generic"
        results = [
            {
                "title": f"{prefix} source {index}",
                "url": f"https://{prefix}-{index}.example/record",
                "fetch_url": f"https://{prefix}-{index}.example/record",
            }
            for index in range(count)
        ]
        return [
            {
                "query": values[0] if values else "",
                "answer": "",
                "results": results,
                "error": None,
            }
        ]

    def fetch_urls(self, requests):
        values = list(requests)
        self.fetch_calls += 1
        self.fetch_vectors.append(values)
        targeted = bool(values and "target-" in values[0]["url"])
        content = (
            "Alpha Phone official record: Release Date 2024-09-20."
            if targeted
            else "Generic product history without the requested release date."
        )
        return [
            {
                "query": request.get("query", ""),
                "answer": "",
                "results": [
                    {
                        "title": request.get("title", ""),
                        "url": request["url"],
                        "raw_content": content,
                    }
                ],
                "error": None,
            }
            for request in values
        ]


class TargetAndGateTests(unittest.TestCase):
    def test_targets_are_stable_unknown_cells_and_queries_have_no_values(self) -> None:
        baseline = table(alpha_date="Unknown", beta_maker="Unknown")
        targets = unknown_cell_targets(baseline)
        self.assertEqual(
            [(item["row_ordinal"], item["column_index"]) for item in targets],
            [(0, 1), (1, 2)],
        )
        self.assertIn('"Alpha Phone" "Release Date"', targets[0]["query"])
        self.assertNotIn("2024-09-20", targets[0]["query"])

    def test_gate_accepts_two_sources_but_rejects_one(self) -> None:
        target = unknown_cell_targets(table())
        batches = Search(targeted_sources=2).fetch_urls(
            [
                {"url": f"https://target-{index}.example/record", "query": "", "title": ""}
                for index in range(2)
            ]
        )
        pages = _independent_pages(batches, page_chars=5_000)
        candidate, admissions, counts = _gate_unknown_candidate(
            baseline=table(),
            proposed=table("2024-09-20"),
            evidence_declarations=json.loads(revision())["cell_evidence"],
            targeted_pages=pages,
            targets=target,
        )
        self.assertIn("| Alpha Phone | 2024-09-20 | Acme |", candidate)
        self.assertEqual(counts["admitted_cell_change_count"], 1)
        self.assertTrue(admissions[0]["admitted"])

        one_page = pages[:1]
        candidate, admissions, counts = _gate_unknown_candidate(
            baseline=table(),
            proposed=table("2024-09-20"),
            evidence_declarations=[
                {
                    "row_key": "Alpha Phone",
                    "column": "Release Date",
                    "evidence_ids": ["R0001"],
                }
            ],
            targeted_pages=one_page,
            targets=target,
        )
        self.assertEqual(candidate, table())
        self.assertEqual(counts["admitted_cell_change_count"], 0)
        self.assertFalse(admissions[0]["admitted"])

    def test_any_forbidden_mutation_fails_the_revision_closed(self) -> None:
        pages = _independent_pages(
            Search(targeted_sources=2).fetch_urls(
                [
                    {"url": f"https://target-{index}.example/record", "query": "", "title": ""}
                    for index in range(2)
                ]
            ),
            page_chars=5_000,
        )
        candidate, admissions, counts = _gate_unknown_candidate(
            baseline=table(),
            proposed=table("2024-09-20", "Changed Maker"),
            evidence_declarations=json.loads(revision())["cell_evidence"],
            targeted_pages=pages,
            targets=unknown_cell_targets(table()),
        )
        self.assertEqual(candidate, table())
        self.assertEqual(admissions, [])
        self.assertEqual(counts["forbidden_mutation_count"], 1)
        self.assertEqual(counts["admitted_cell_change_count"], 0)

    def test_subdomain_aliases_are_one_source_and_final_redirects_are_filtered(
        self,
    ) -> None:
        batches = [
            {
                "query": "q",
                "results": [
                    {"title": "a", "url": "https://a.publisher.example/one"},
                    {"title": "b", "url": "https://b.publisher.example/two"},
                    {"title": "c", "url": "https://independent.example/three"},
                ],
            }
        ]
        leads, eligible = _selected_leads(
            batches,
            excluded_sources=set(),
            excluded_urls=set(),
            limit=4,
        )
        self.assertEqual(len(leads), 2)
        self.assertEqual(eligible, {"publisher.example", "independent.example"})

        redirected = [
            {
                "query": "q",
                "results": [
                    {
                        "title": "generic redirect",
                        "url": "https://generic-0.example/final",
                        "raw_content": "Alpha Phone 2024-09-20",
                    },
                    {
                        "title": "new source",
                        "url": "https://new-source.example/final",
                        "raw_content": "Alpha Phone 2024-09-20",
                    },
                ],
            }
        ]
        pages = _independent_pages(
            redirected,
            page_chars=5_000,
            excluded_sources={"generic-0.example"},
        )
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["host"], "new-source.example")


class RuntimeTests(unittest.TestCase):
    def test_two_plus_one_query_six_plus_four_fetch_and_safe_fill(self) -> None:
        model = Model()
        search = Search()
        result = run_v24655_task(
            TASK, model=model, search=search, limits=limits(), monotonic=time.monotonic
        )
        validate_result(result)
        receipt = result["receipt"]
        self.assertEqual(model.requests, 3)
        self.assertEqual([len(vector) for vector in search.search_vectors], [2, 1])
        self.assertEqual([len(vector) for vector in search.fetch_vectors], [6, 4])
        self.assertEqual(receipt["admitted_logical_query_count"], 3)
        self.assertEqual(receipt["admitted_total_fetch_targets"], 10)
        self.assertEqual(receipt["selected_unknown_target_count"], 1)
        self.assertEqual(receipt["admitted_cell_change_count"], 1)
        self.assertIn(
            "| Alpha Phone | 2024-09-20 | Acme |",
            result["predictions"]["unknown_cell_targeted"],
        )
        self.assertFalse(receipt["positive_task_credit_assigned"])

    def test_insufficient_sources_and_recovery_return_identity_candidate(self) -> None:
        result = run_v24655_task(
            TASK,
            model=Model(),
            search=Search(targeted_sources=1),
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertEqual(
            result["predictions"]["baseline"],
            result["predictions"]["unknown_cell_targeted"],
        )
        self.assertEqual(result["receipt"]["admitted_cell_change_count"], 0)

        recovery_model = Model(
            [
                json.dumps({"columns": ["wrong"], "queries": ["one", "two"]}),
                RuntimeError("private provider failure"),
                table(),
            ]
        )
        search = Search()
        recovered = run_v24655_task(
            TASK,
            model=recovery_model,
            search=search,
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertEqual(
            recovered["predictions"]["baseline"],
            recovered["predictions"]["unknown_cell_targeted"],
        )
        self.assertEqual(len(search.search_vectors), 1)
        self.assertEqual(recovered["receipt"]["selected_unknown_target_count"], 0)
        self.assertNotIn("private provider failure", json.dumps(recovered))

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24655_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_vectors, [])
        self.assertEqual(search.fetch_vectors, [])

    def test_result_tamper_and_runtime_capability_fail_closed(self) -> None:
        model = Model()
        result = run_v24655_task(
            TASK, model=model, search=Search(), limits=limits(), monotonic=time.monotonic
        )
        tampered = copy.deepcopy(result)
        tampered["receipt"]["admitted_cell_change_count"] += 1
        reseal(tampered)
        with self.assertRaises(ValueError):
            validate_result(tampered)

        rebound = copy.deepcopy(result)
        rebound["receipt"]["cell_admissions"][0]["change_binding_sha256"] = "0" * 64
        rebound["receipt"]["cell_admissions"][0]["support_receipt"][
            "change_binding_sha256"
        ] = "0" * 64
        reseal(rebound)
        with self.assertRaises(ValueError):
            validate_result(rebound)

        stats = copy.deepcopy(result)
        stats["receipt"]["baseline_table"]["completion_ratio"] = 0.0
        reseal(stats)
        with self.assertRaises(ValueError):
            validate_result(stats)

        retargeted = copy.deepcopy(result)
        retargeted["receipt"]["cell_admissions"][0]["row_ordinal"] = 1
        reseal(retargeted)
        with self.assertRaises(ValueError):
            validate_result(retargeted)

        receipt = result["receipt"]
        self.assertEqual(receipt["logical_model_admission_count"], model.requests)
        self.assertEqual(receipt["pre_provider_model_rejection_count"], 0)
        self.assertFalse(
            receipt["cell_admissions"][0]["support_receipt"][
                "entropy_information_gain_evaluator_or_task_credit_used"
            ]
        )

        source = (
            ROOT / "src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py"
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
        privileged = {
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
        self.assertFalse(reads & privileged)


if __name__ == "__main__":
    unittest.main()
