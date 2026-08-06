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
from deepwide_agent.v24639_ror_objective_runtime import extract_visible_entities
from deepwide_agent.v24640_evidence_constrained_runtime import (
    ARMS,
    gate_replacements,
    run_v24640_task,
    validate_result,
)
from deepwide_agent.v24640_ror_external_contract import (
    ENTITY_GROUPS,
    LIMITS,
    task_vector,
    visible_task,
)
from deepwide_agent.v24640_ror_external_evaluator import (
    evaluate_frozen_rows,
    evaluate_prediction,
    gold_rows,
)


def table(rows: list[list[str]]) -> str:
    return (
        "```markdown\n| Organization | ROR ID | Country code |\n"
        "| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class Model:
    def __init__(self, task: dict[str, str]) -> None:
        self.task = task
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.calls: list[tuple[bool, str]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        self.calls.append((json_mode, user))
        entities = extract_visible_entities(self.task["question"])
        if self.requests == 1:
            value = {
                "language": "English",
                "columns": ["Organization", "ROR ID", "Country code"],
                "row_target_hint": "4",
                "queries": ["ignored because the visible vector is authoritative"],
            }
            text = json.dumps(value)
        elif self.requests == 2:
            text = table(
                [
                    [entities[0], "Unknown", "IN"],
                    [entities[1], "099999999", "EE"],
                    [entities[2], "Unknown", "DE"],
                    [entities[3], "Unknown", "AU"],
                ]
            )
        else:
            text = json.dumps(
                {
                    "replacements": [
                        {
                            "organization": entities[0],
                            "ror_id": "00146e793",
                            "evidence_ids": ["E0001"],
                        },
                        {
                            "organization": entities[1],
                            "ror_id": "01njn7795",
                            "evidence_ids": ["E0002"],
                        },
                    ]
                }
            )
        return ModelResult(text, {}, None, 1)


class Search:
    def __init__(self, entities: list[str]) -> None:
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
        self.entities = entities
        self.queries: list[str] = []
        self.fetch_count = 0

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.queries = list(queries)
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "title": entity,
                        "url": f"https://example.test/{index}",
                        "fetch_url": f"https://example.test/{index}",
                    }
                ],
                "error": None,
            }
            for index, (entity, query) in enumerate(zip(self.entities, queries, strict=True), 1)
        ]

    def fetch_urls(self, requests):
        self.fetch_calls += 1
        values = list(requests)
        self.fetch_count = len(values)
        suffixes = ("00146e793", "01njn7795", "00kg2yq63", "00rev1511")
        return [
            {
                "query": request["query"],
                "answer": "",
                "results": [
                    {
                        "title": self.entities[index],
                        "url": request["url"],
                        "raw_content": (
                            f"The ROR record for {self.entities[index]} is "
                            f"https://ror.org/{suffixes[index]}."
                        ),
                    }
                ],
                "error": None,
            }
            for index, request in enumerate(values)
        ]


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entities = ["Alpha Research Institute", "Beta Foundation"]
        self.baseline = table(
            [
                [self.entities[0], "Unknown", "FR"],
                [self.entities[1], "012345678", "US"],
            ]
        )

    def gate(self, pages, declarations):
        return gate_replacements(
            self.baseline,
            entities=self.entities,
            pages=pages,
            declarations=declarations,
        )

    def test_exact_entity_suffix_and_declared_page_are_required(self) -> None:
        exact = {
            "evidence_id": "E0001",
            "title": "Alpha Research Institute",
            "url": "https://ror.org/01abc2d34",
            "content": "Official profile for Alpha Research Institute.",
        }
        declarations = [
            {
                "organization": self.entities[0],
                "ror_id": "01abc2d34",
                "evidence_ids": ["E0001"],
            }
        ]
        candidate, receipt = self.gate([exact], declarations)
        self.assertIn("| Alpha Research Institute | 01abc2d34 | FR |", candidate)
        self.assertEqual(receipt["admitted_replacement_count"], 1)

        rejected_pages = {
            "entity_only": [{**exact, "url": "https://example.test/no-ror"}],
            "ror_only": [{**exact, "title": "Unrelated Institute", "content": "unrelated"}],
            "partial_entity": [
                {**exact, "title": "Alpha Research", "content": "Official profile."}
            ],
        }
        for label, pages in rejected_pages.items():
            with self.subTest(label=label):
                candidate, receipt = self.gate(pages, declarations)
                self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
                self.assertEqual(receipt["admitted_replacement_count"], 0)

        wrong_id = [{**declarations[0], "evidence_ids": ["E9999"]}]
        candidate, receipt = self.gate([exact], wrong_id)
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_conflict_fails_closed(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "title": self.entities[0],
                "url": "https://ror.org/01abc2d34",
                "content": self.entities[0],
            },
            {
                "evidence_id": "E0002",
                "title": self.entities[0],
                "url": "https://ror.org/01xyz9w87",
                "content": self.entities[0],
            },
        ]
        declarations = [
            {
                "organization": self.entities[0],
                "ror_id": suffix,
                "evidence_ids": [evidence_id],
            }
            for suffix, evidence_id in (("01abc2d34", "E0001"), ("01xyz9w87", "E0002"))
        ]
        candidate, receipt = self.gate(pages, declarations)
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["conflicting_target_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_nonunknown_ror_and_every_country_cell_are_immutable(self) -> None:
        page = {
            "evidence_id": "E0001",
            "title": self.entities[1],
            "url": "https://ror.org/01abc2d34",
            "content": self.entities[1],
        }
        declarations = [
            {
                "organization": self.entities[1],
                "ror_id": "01abc2d34",
                "evidence_ids": ["E0001"],
                "country_code": "ZZ",
            }
        ]
        candidate, receipt = self.gate([page], declarations)
        self.assertIn("| Beta Foundation | 012345678 | US |", candidate)
        self.assertEqual(receipt["nonunknown_target_proposal_count"], 1)
        self.assertFalse(receipt["existing_nonunknown_cells_changed"])
        self.assertFalse(receipt["country_code_cells_changed"])

    def test_no_support_preserves_unknown(self) -> None:
        candidate, receipt = self.gate([], [])
        self.assertEqual(candidate, self.baseline)
        self.assertEqual(receipt["admitted_replacement_count"], 0)


class RuntimeTests(unittest.TestCase):
    def test_visible_boundary_and_fresh_vector(self) -> None:
        tasks = task_vector()
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        for index, task in enumerate(tasks):
            self.assertEqual(
                extract_visible_entities(task["question"]), list(ENTITY_GROUPS[index])
            )

    def test_effect_conservation_and_monotonic_revision(self) -> None:
        task = visible_task(1)
        entities = extract_visible_entities(task["question"])
        model = Model(task)
        search = Search(entities)
        result = run_v24640_task(
            task,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**LIMITS),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertEqual(model.requests, 3)
        self.assertEqual(len(search.queries), 4)
        self.assertLessEqual(search.fetch_count, 10)
        self.assertEqual(
            result["receipt"]["model_stage_vector"],
            ["shared_plan", "baseline_synthesis", "evidence_constrained_revision"],
        )
        self.assertTrue(
            result["receipt"]["candidate_uses_frozen_third_dependent_model_effect"]
        )
        self.assertFalse(
            result["receipt"]["total_model_query_fetch_effect_budget_changed_from_v24639"]
        )
        self.assertFalse(result["receipt"]["entropy_shadow"]["routes_or_changes_forward_effects"])
        self.assertEqual(set(result["predictions"]), set(ARMS))
        self.assertIn("| " + entities[0] + " | 00146e793 | IN |", result["predictions"]["evidence_constrained"])
        self.assertIn("| " + entities[1] + " | 099999999 | EE |", result["predictions"]["evidence_constrained"])

    def test_forward_ast_has_no_evaluator_or_gold_capability(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24640_evidence_constrained_runtime.py",
            ROOT / "src/deepwide_agent/v24640_ror_external_contract.py",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any("evaluator" in name or "gold" in name for name in imports)
            )
            self.assertNotIn("evaluation/", text)
            self.assertNotIn("subprocess", text)
            self.assertNotIn("_arm_order =", text)


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gold = gold_rows(
            (ROOT / "evaluation/v24640_ror_gold_v1.csv").read_text(encoding="utf-8")
        )

    def test_gold_fixed_denominator(self) -> None:
        self.assertEqual(len(self.gold), 48)
        self.assertEqual(len({row["opaque_id"] for row in self.gold}), 12)

    def test_full_ror_url_is_semantically_equivalent(self) -> None:
        rows = [
            row for row in self.gold if row["opaque_id"] == visible_task(1)["opaque_id"]
        ]
        exact = table(
            [
                [
                    row["Organization"],
                    "https://ror.org/" + row["ROR ID"],
                    row["Country code"],
                ]
                for row in rows
            ]
        )
        self.assertEqual(evaluate_prediction(exact, rows)["exact_table_success"], 1)

    def test_gate_requires_exact_gain_composite_and_item_guardrails(self) -> None:
        predictions = []
        for task in task_vector():
            rows = [row for row in self.gold if row["opaque_id"] == task["opaque_id"]]
            exact = table(
                [
                    [row["Organization"], row["ROR ID"], row["Country code"]]
                    for row in rows
                ]
            )
            predictions.append(
                {
                    "opaque_id": task["opaque_id"],
                    "predictions": {
                        "baseline": "broken",
                        "evidence_constrained": exact,
                    },
                }
            )
        result = evaluate_frozen_rows(predictions, self.gold)
        self.assertTrue(result["gate_passed"])
        self.assertEqual(
            result["candidate_minus_baseline"]["exact_table_successes"], 12
        )
        self.assertGreaterEqual(result["candidate_minus_baseline"]["item_f1"], 0)


if __name__ == "__main__":
    unittest.main()
