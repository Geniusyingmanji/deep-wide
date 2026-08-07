from __future__ import annotations

import ast
import copy
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    build_target_segment_catalog,
)
from deepwide_agent.v24743_generic_record_binding import (  # noqa: E402
    _baseline_matrix,
)
from deepwide_agent import v24770_visible_entity_fair_semantic_runtime as target  # noqa: E402


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


def lead(entity: str, source: str, *, title: str | None = None, suffix: str = "record") -> dict:
    return {
        "title": title if title is not None else f"{entity} institutional profile",
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
            value = {
                "language": "English",
                "columns": ["Organization", "Founded", "Country"],
                "row_target_hint": "4",
                "queries": ["generic query one", "generic query two", "three", "four"],
            }
            return ModelResult(json.dumps(value), {}, None, 1)
        return ModelResult(BASELINE, {}, None, 1)


class Search:
    def __init__(self, values: list[dict], contents: dict[str, str]) -> None:
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
        self.seen_queries: list[str] = []
        self.seen_fetches: list[str] = []

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
        self.fetch_calls += len(requests)
        self.seen_fetches = [request["url"] for request in requests]
        return [
            {
                "query": "fetch",
                "answer": "",
                "results": [
                    {
                        "title": request.get("title", ""),
                        "url": request["url"],
                        "fetch_url": request["url"],
                        "requested_url": request["url"],
                        "content": "",
                        "raw_content": self.contents[request["url"]],
                        "fetch_status": "ok",
                    }
                ],
                "error": None,
            }
            for request in requests
        ]


class V24770VisibleEntityFairSemanticRuntimeTests(unittest.TestCase):
    def test_visible_queries_are_entity_specific_and_fixed_cap(self) -> None:
        self.assertEqual(target.extract_visible_entities(QUESTION), list(ENTITIES))
        queries = target.visible_entity_query_vector(QUESTION, 4)
        self.assertEqual(len(queries), 4)
        for entity, query in zip(ENTITIES, queries, strict=True):
            self.assertIn(f'"{entity}"', query)
        with self.assertRaises(ValueError):
            target.visible_entity_query_vector(QUESTION, 3)
        with self.assertRaises(ValueError):
            target.visible_entity_query_vector(
                QUESTION.replace(
                    "Organization, Founded, Country",
                    "Organization, Revenue, Country",
                ),
                4,
            )
        with self.assertRaises(ValueError):
            target.extract_visible_entities(QUESTION.replace("2. ", "3. ", 1))

    def test_round_robin_prevents_first_entity_from_consuming_ten_slots(self) -> None:
        values = [
            lead(ENTITIES[0], f"alpha{index}.example", suffix=str(index))
            for index in range(1, 9)
        ]
        values += [
            lead(ENTITIES[1], "beta.example"),
            lead(ENTITIES[2], "gamma.example"),
            lead(ENTITIES[3], "delta.example"),
        ]
        selected, diagnostic = target.select_visible_entity_fair_leads(
            values, entities=ENTITIES
        )
        self.assertEqual(len(selected), 10)
        self.assertEqual(diagnostic["round_robin_assignment_count_vector"], [7, 1, 1, 1])
        self.assertEqual(diagnostic["post_round_robin_fill_count"], 0)
        self.assertEqual(
            diagnostic["selected_aligned_source_count_vector"], [7, 1, 1, 1]
        )
        urls = [item["url"] for item in selected]
        self.assertLess(urls.index("https://beta.example/record"), 4)
        self.assertLess(urls.index("https://gamma.example/record"), 4)
        self.assertLess(urls.index("https://delta.example/record"), 4)

    def test_query_only_and_url_query_fragment_do_not_establish_alignment(self) -> None:
        values = [
            {
                "title": "Generic institutional page",
                "url": "https://generic.example/record?q=Alpha%20Institute#Alpha-Institute",
                "fetch_url": "https://generic.example/record?q=Alpha%20Institute#Alpha-Institute",
                "query": '"Alpha Institute" founded',
            },
            lead(ENTITIES[1], "beta.example"),
        ]
        selected, diagnostic = target.select_visible_entity_fair_leads(
            values, entities=ENTITIES
        )
        self.assertEqual(diagnostic["aligned_independent_source_count_vector"], [0, 1, 0, 0])
        self.assertEqual(diagnostic["round_robin_assignment_count_vector"], [0, 1, 0, 0])
        self.assertEqual(diagnostic["post_round_robin_fill_count"], 1)
        self.assertEqual(selected[0]["url"], "https://beta.example/record")

    def test_round_robin_prefers_global_source_diversity_across_entities(self) -> None:
        values = [
            lead(
                ENTITIES[0],
                "shared.example",
                title=f"{ENTITIES[0]} and {ENTITIES[1]} institutional profile",
            ),
            lead(ENTITIES[0], "alpha.example"),
            lead(ENTITIES[1], "beta.example"),
            lead(ENTITIES[2], "gamma.example"),
            lead(ENTITIES[3], "delta.example"),
        ]
        selected, diagnostic = target.select_visible_entity_fair_leads(
            values, entities=ENTITIES
        )
        self.assertEqual(diagnostic["selected_fetch_lead_count"], 5)
        self.assertEqual(diagnostic["selected_unique_source_count"], 5)
        self.assertEqual(diagnostic["round_robin_assignment_count_vector"], [2, 1, 1, 1])

    def test_semantic_two_source_projection_changes_unknown_without_new_effect(self) -> None:
        values = [
            lead(ENTITIES[0], "alpha-one.example"),
            lead(ENTITIES[1], "beta.example"),
            lead(ENTITIES[2], "gamma.example"),
            lead(ENTITIES[3], "delta.example"),
            lead(ENTITIES[0], "alpha-two.example"),
        ]
        contents = {
            item["url"]: (
                f"{ENTITIES[0]} was founded in 1999."
                if "alpha-" in item["url"]
                else f"{item['title']}. No explicit founding relation here."
            )
            for item in values
        }
        model = Model()
        search = Search(values, contents)
        result = target.run_v24770_task(
            TASK, model=model, search=search, limits=LIMITS, monotonic=time.monotonic
        )
        self.assertEqual(target.validate_result(result), result)
        self.assertEqual(search.seen_queries, target.visible_entity_query_vector(QUESTION, 4))
        self.assertEqual(model.requests, 2)
        self.assertEqual(search.calls, 1)
        self.assertEqual(search.fetch_calls, 5)
        self.assertIn("| Alpha Institute | 1999 | Unknown |", result["predictions"]["entity_fair_semantic"])
        receipt = result["semantic_receipt"]
        self.assertEqual(receipt["semantic_unknown_projection_count"], 2)
        self.assertEqual(receipt["semantic_unknown_eligible_support_set_count"], 1)
        self.assertEqual(receipt["final_changed_cell_count"], 1)
        self.assertFalse(receipt["new_model_search_fetch_or_evaluator_effect"])
        self.assertFalse(receipt["positive_entropy_or_task_credit_assigned"])

    def test_search_failure_is_valid_zero_fetch_and_zero_coverage(self) -> None:
        values = [lead(entity, f"source{index}.example") for index, entity in enumerate(ENTITIES)]
        contents = {item["url"]: "No explicit relation." for item in values}
        search = Search(values, contents)
        with patch.object(search, "search_many", side_effect=RuntimeError("provider")):
            result = target.run_v24770_task(
                TASK,
                model=Model(),
                search=search,
                limits=LIMITS,
                monotonic=time.monotonic,
            )
        receipt = result["scheduler_receipt"]
        self.assertEqual(receipt["search_invocation_count"], 1)
        self.assertEqual(receipt["provider_search_failure_count"], 1)
        self.assertEqual(receipt["planner_query_count"], 4)
        self.assertEqual(receipt["fetch_invocation_count"], 0)
        self.assertEqual(receipt["fetch_request_count"], 0)
        self.assertEqual(receipt["requested_aligned_source_count_vector"], [0, 0, 0, 0])
        self.assertEqual(search.fetch_calls, 0)
        self.assertEqual(
            result["predictions"]["entity_fair_semantic"],
            result["predictions"]["baseline"],
        )

    def test_one_source_abstains_and_conflicting_two_source_values_abstain(self) -> None:
        for years in (("1999",), ("1999", "2001")):
            values = [
                lead(ENTITIES[0], f"alpha-{index}.example", suffix=str(index))
                for index in range(len(years))
            ]
            values += [
                lead(ENTITIES[1], "beta.example"),
                lead(ENTITIES[2], "gamma.example"),
                lead(ENTITIES[3], "delta.example"),
            ]
            contents = {
                item["url"]: (
                    f"{ENTITIES[0]} was founded in {years[index]}."
                    if index < len(years)
                    else "No explicit founding relation."
                )
                for index, item in enumerate(values)
            }
            result = target.run_v24770_task(
                TASK,
                model=Model(),
                search=Search(values, contents),
                limits=LIMITS,
                monotonic=time.monotonic,
            )
            self.assertEqual(
                result["predictions"]["entity_fair_semantic"],
                result["predictions"]["baseline"],
            )
            self.assertEqual(result["semantic_receipt"]["final_changed_cell_count"], 0)

    def test_parent_exact_and_semantic_same_value_merge_once_but_conflict_abstains(self) -> None:
        pages = [
            {
                "host": "one.example",
                "content": f"{ENTITIES[0]} was founded in 1999.",
                "fetch_integrity": True,
            },
            {
                "host": "two.example.net",
                "content": f"{ENTITIES[0]} was founded in 1999.",
                "fetch_integrity": True,
            },
        ]
        columns, rows = _baseline_matrix(BASELINE)
        catalog = build_target_segment_catalog(
            [
                {"row_key": row[0], "column": columns[index], "old_value": row[index]}
                for row in rows
                for index in range(1, len(columns))
            ],
            pages,
            [],
        )
        exact_same = BASELINE.replace(
            "| Alpha Institute | Unknown | Unknown |",
            "| Alpha Institute | 1999 | Unknown |",
        )
        parent = {"predictions": {"baseline": BASELINE, "generic_structured": exact_same}}
        candidate, receipt = target._semantic_candidate(parent, entities=ENTITIES, catalog=catalog)
        self.assertIn("| Alpha Institute | 1999 | Unknown |", candidate)
        self.assertEqual(receipt["parent_and_semantic_same_value_cell_count"], 1)
        self.assertEqual(receipt["final_changed_cell_count"], 1)
        exact_conflict = BASELINE.replace(
            "| Alpha Institute | Unknown | Unknown |",
            "| Alpha Institute | 2001 | Unknown |",
        )
        parent = {"predictions": {"baseline": BASELINE, "generic_structured": exact_conflict}}
        candidate, receipt = target._semantic_candidate(parent, entities=ENTITIES, catalog=catalog)
        self.assertEqual(candidate, BASELINE)
        self.assertEqual(receipt["parent_and_semantic_value_conflict_cell_count"], 1)
        self.assertEqual(receipt["final_conflict_abstention_cell_count"], 1)

    def test_support_set_must_be_projection_backed_on_every_source(self) -> None:
        pages = [
            {
                "host": "one.example",
                "content": f"{ENTITIES[0]} was founded in 1999.",
                "fetch_integrity": True,
            },
            {
                "host": "two.example.net",
                "content": f"{ENTITIES[0]} Founded | 1999",
                "fetch_integrity": True,
            },
        ]
        columns, rows = _baseline_matrix(BASELINE)
        catalog = build_target_segment_catalog(
            [
                {"row_key": row[0], "column": columns[index], "old_value": row[index]}
                for row in rows
                for index in range(1, len(columns))
            ],
            pages,
            [],
        )
        self.assertEqual(catalog["semantic_projection_count"], 1)
        self.assertEqual(catalog["eligible_support_set_count"], 1)
        parent = {"predictions": {"baseline": BASELINE, "generic_structured": BASELINE}}
        candidate, receipt = target._semantic_candidate(parent, entities=ENTITIES, catalog=catalog)
        self.assertEqual(candidate, BASELINE)
        self.assertEqual(receipt["semantic_catalog_eligible_support_set_count"], 1)
        self.assertEqual(receipt["semantic_unknown_eligible_support_set_count"], 0)
        self.assertEqual(receipt["projection_backed_eligible_support_set_count"], 0)
        self.assertEqual(receipt["final_changed_cell_count"], 0)

    def test_nonunknown_eligible_support_is_ignored_without_mutation(self) -> None:
        baseline = BASELINE.replace(
            "| Alpha Institute | Unknown | Unknown |",
            "| Alpha Institute | 1999 | Unknown |",
        )
        pages = [
            {
                "host": f"source{index}.example",
                "content": f"{ENTITIES[0]} was founded in 2001.",
                "fetch_integrity": True,
            }
            for index in range(3)
        ]
        columns, rows = _baseline_matrix(baseline)
        catalog = build_target_segment_catalog(
            [
                {"row_key": row[0], "column": columns[index], "old_value": row[index]}
                for row in rows
                for index in range(1, len(columns))
            ],
            pages,
            [],
        )
        self.assertGreaterEqual(catalog["eligible_support_set_count"], 1)
        parent = {"predictions": {"baseline": baseline, "generic_structured": baseline}}
        candidate, receipt = target._semantic_candidate(parent, entities=ENTITIES, catalog=catalog)
        self.assertEqual(candidate, baseline)
        self.assertEqual(receipt["semantic_unknown_eligible_support_set_count"], 0)
        self.assertEqual(receipt["final_changed_cell_count"], 0)

    def test_visible_identity_drift_discards_parent_change(self) -> None:
        baseline = BASELINE.replace("Alpha Institute", "Wrong Institute")
        exact = baseline.replace(
            "| Wrong Institute | Unknown | Unknown |",
            "| Wrong Institute | 1999 | Unknown |",
        )
        parent = {"predictions": {"baseline": baseline, "generic_structured": exact}}
        candidate, receipt = target._semantic_candidate(
            parent, entities=ENTITIES, catalog=None
        )
        self.assertEqual(candidate, baseline)
        self.assertFalse(receipt["identity_surface_eligible"])
        self.assertEqual(receipt["parent_exact_adapter_changed_cell_count"], 1)
        self.assertEqual(receipt["semantic_boundary_target_count"], 0)
        self.assertEqual(receipt["semantic_unknown_target_count"], 0)
        self.assertEqual(receipt["final_changed_cell_count"], 0)

    def test_result_and_receipt_tamper_fail_closed(self) -> None:
        values = [lead(entity, f"source{index}.example") for index, entity in enumerate(ENTITIES)]
        contents = {item["url"]: "No explicit relation." for item in values}
        result = target.run_v24770_task(
            TASK,
            model=Model(),
            search=Search(values, contents),
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        altered = copy.deepcopy(result)
        altered["scheduler_receipt"]["query_text_used_to_establish_alignment"] = True
        altered["scheduler_receipt"].pop("receipt_sha256")
        altered["scheduler_receipt"]["receipt_sha256"] = target.payload_sha256(
            altered["scheduler_receipt"]
        )
        altered.pop("result_sha256")
        altered["result_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_result(altered)
        altered = copy.deepcopy(result)
        altered["private_visible_entities"][0] = "Forged Entity"
        altered["private_scheduler_state"]["visible_entities"][0] = "Forged Entity"
        altered["private_scheduler_state"]["entity_queries"][0] = (
            '"Forged Entity" founded established country'
        )
        with self.assertRaises(ValueError):
            target._scheduler_receipt(altered["private_scheduler_state"])
        altered["scheduler_receipt"]["receipt_sha256"] = target.payload_sha256(
            {
                key: value
                for key, value in altered["scheduler_receipt"].items()
                if key != "receipt_sha256"
            }
        )
        altered.pop("result_sha256")
        altered["result_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_result(altered)
        altered = copy.deepcopy(result)
        altered["predictions"]["entity_fair_semantic"] = altered["predictions"][
            "entity_fair_semantic"
        ].replace("Unknown", "2001", 1)
        altered["prediction_sha256"]["entity_fair_semantic"] = target.hashlib.sha256(
            altered["predictions"]["entity_fair_semantic"].encode()
        ).hexdigest()
        altered.pop("result_sha256")
        altered["result_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_result(altered)

    def test_runtime_is_label_blind_and_has_no_evaluator_import(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        privileged = {
            "answer_key",
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
        accesses = []
        imports = []
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
                accesses.append(node.lineno)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        self.assertEqual(accesses, [])
        self.assertFalse(any("evaluator" in name.casefold() for name in imports))


if __name__ == "__main__":
    unittest.main()
