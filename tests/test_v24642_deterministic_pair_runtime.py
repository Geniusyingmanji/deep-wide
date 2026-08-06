from __future__ import annotations

import ast
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
from deepwide_agent.v24637_objective_alignment_runtime import payload_sha256
from deepwide_agent.v24639_ror_objective_runtime import extract_visible_entities
from deepwide_agent.v24642_deterministic_pair_runtime import (
    ARMS,
    discover_pairs,
    entity_bound_ror_suffixes,
    explicit_ror_suffixes,
    run_v24642_task,
    validate_result,
)
from deepwide_agent.v24642_ror_external_contract import (
    ENTITY_GROUPS,
    LIMITS,
    task_vector,
    visible_task,
)


def table(rows: list[list[str]]) -> str:
    return (
        "```markdown\n| Organization | ROR ID | Country code |\n"
        "| --- | --- | --- |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class PairDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entities = [
            "Alpha Research Institute",
            "Beta Foundation",
            "Gamma Laboratory",
            "Delta Centre",
        ]
        self.baseline = table(
            [
                [self.entities[0], "Unknown", "FR"],
                [self.entities[1], "012345678", "US"],
                [self.entities[2], "Unknown", "DE"],
                [self.entities[3], "Unknown", "AU"],
            ]
        )

    def test_explicit_url_or_label_required(self) -> None:
        url_page = {
            "url": "https://ror.org/01abc2d34",
            "title": "Alpha Research Institute",
            "content": "Official profile.",
        }
        label_page = {
            "url": "https://example.test/profile",
            "title": "Alpha Research Institute",
            "content": "ROR ID: 01abc2d34",
        }
        bare_page = {
            "url": "https://example.test/profile",
            "title": "Alpha Research Institute",
            "content": "internal reference 01abc2d34",
        }
        self.assertEqual(explicit_ror_suffixes(url_page), ("01abc2d34",))
        self.assertEqual(explicit_ror_suffixes(label_page), ("01abc2d34",))
        self.assertEqual(explicit_ror_suffixes(bare_page), ())

    def test_unique_exact_pair_is_admitted(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "url": "https://ror.org/01abc2d34",
                "title": self.entities[0],
                "content": "Official profile for Alpha Research Institute.",
            }
        ]
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=pages
        )
        self.assertIn("| Alpha Research Institute | 01abc2d34 | FR |", candidate)
        self.assertEqual(receipt["unknown_target_unique_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 1)

    def test_official_ror_page_url_binds_to_exact_body_entity(self) -> None:
        page = {
            "evidence_id": "E0001",
            "url": "https://ror.org/01abc2d34",
            "title": "Research organization profile",
            "content": "Official profile for Alpha Research Institute.",
        }
        self.assertEqual(
            entity_bound_ror_suffixes(page, self.entities[0]), ("01abc2d34",)
        )
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=[page]
        )
        self.assertIn("| Alpha Research Institute | 01abc2d34 | FR |", candidate)
        self.assertEqual(receipt["admitted_replacement_count"], 1)

    def test_partial_entity_bare_id_and_no_pair_preserve_unknown(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "url": "https://example.test/profile",
                "title": "Alpha Research",
                "content": "internal reference 01abc2d34",
            }
        ]
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=pages
        )
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["admitted_replacement_count"], 0)
        self.assertEqual(receipt["unknown_target_no_pair_count"], 3)

    def test_distant_directory_id_is_not_cross_bound(self) -> None:
        page = {
            "evidence_id": "E0001",
            "url": "https://example.test/directory",
            "title": "Organization directory",
            "content": (
                "Alpha Research Institute profile. "
                + ("unrelated directory text " * 80)
                + "Beta Foundation ROR ID: 01abc2d34"
            ),
        }
        self.assertEqual(entity_bound_ror_suffixes(page, self.entities[0]), ())
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=[page]
        )
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_multi_id_page_or_cross_page_conflict_fails_closed(self) -> None:
        ambiguous = {
            "evidence_id": "E0001",
            "url": "https://example.test/profile",
            "title": self.entities[0],
            "content": (
                "Alpha Research Institute ROR ID: 01abc2d34 and historical "
                "ROR ID: 01xyz9w87"
            ),
        }
        unique = {
            "evidence_id": "E0002",
            "url": "https://ror.org/01abc2d34",
            "title": self.entities[0],
            "content": self.entities[0],
        }
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=[ambiguous, unique]
        )
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["unknown_target_ambiguous_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

        conflict = {
            "evidence_id": "E0003",
            "url": "https://ror.org/01xyz9w87",
            "title": self.entities[0],
            "content": self.entities[0],
        }
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=[unique, conflict]
        )
        self.assertIn("| Alpha Research Institute | Unknown | FR |", candidate)
        self.assertEqual(receipt["unknown_target_ambiguous_pair_count"], 1)
        self.assertEqual(receipt["admitted_replacement_count"], 0)

    def test_nonunknown_ror_and_country_are_immutable(self) -> None:
        pages = [
            {
                "evidence_id": "E0001",
                "url": "https://ror.org/01abc2d34",
                "title": self.entities[1],
                "content": self.entities[1],
            }
        ]
        candidate, receipt = discover_pairs(
            self.baseline, entities=self.entities, pages=pages
        )
        self.assertIn("| Beta Foundation | 012345678 | US |", candidate)
        self.assertEqual(receipt["nonunknown_target_pair_count"], 1)
        self.assertFalse(receipt["existing_nonunknown_cells_changed"])
        self.assertFalse(receipt["country_code_cells_changed"])


class Model:
    def __init__(self, task: dict[str, str]) -> None:
        self.task = task
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        entities = extract_visible_entities(self.task["question"])
        if self.requests == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["Organization", "ROR ID", "Country code"],
                    "row_target_hint": "4",
                    "queries": ["ignored"],
                }
            )
        else:
            text = table(
                [
                    [entities[0], "Unknown", "IN"],
                    [entities[1], "099999999", "EE"],
                    [entities[2], "Unknown", "DE"],
                    [entities[3], "Unknown", "AU"],
                ]
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
            for index, (entity, query) in enumerate(
                zip(self.entities, queries, strict=True), 1
            )
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
                        "url": f"https://ror.org/{suffixes[index]}",
                        "raw_content": f"Official profile for {self.entities[index]}.",
                    }
                ],
                "error": None,
            }
            for index, request in enumerate(values)
        ]


class RuntimeTests(unittest.TestCase):
    def test_visible_boundary_and_fresh_vector(self) -> None:
        tasks = task_vector()
        self.assertEqual(len(tasks), 12)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        for index, task in enumerate(tasks):
            self.assertEqual(
                extract_visible_entities(task["question"]), list(ENTITY_GROUPS[index])
            )

    def test_two_provider_calls_and_effect_conservation(self) -> None:
        task = visible_task(1)
        entities = extract_visible_entities(task["question"])
        model = Model(task)
        search = Search(entities)
        result = run_v24642_task(
            task,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**LIMITS),
            monotonic=time.monotonic,
        )
        validate_result(result)
        self.assertEqual(model.requests, 2)
        self.assertEqual(len(search.queries), 4)
        self.assertLessEqual(search.fetch_count, 10)
        self.assertEqual(
            result["receipt"]["provider_model_stage_vector"],
            ["shared_plan", "baseline_synthesis"],
        )
        self.assertEqual(result["receipt"]["model_cost"]["requests"], 2)
        self.assertFalse(
            result["receipt"]["candidate_uses_provider_model_for_pair_declaration"]
        )
        self.assertFalse(
            result["receipt"]["candidate_additional_model_query_fetch_or_token_effect"]
        )
        self.assertEqual(set(result["predictions"]), set(ARMS))
        self.assertIn(
            f"| {entities[0]} | 00146e793 | IN |",
            result["predictions"]["deterministic_pair"],
        )
        self.assertIn(
            f"| {entities[1]} | 099999999 | EE |",
            result["predictions"]["deterministic_pair"],
        )

    def test_result_validator_rejects_country_mutation(self) -> None:
        task = visible_task(1)
        entities = extract_visible_entities(task["question"])
        result = run_v24642_task(
            task,
            model=Model(task),
            search=Search(entities),
            limits=ScoreFirstLimits(**LIMITS),
            monotonic=time.monotonic,
        )
        candidate = result["predictions"]["deterministic_pair"].replace(
            "| EE |", "| ZZ |", 1
        )
        result["predictions"]["deterministic_pair"] = candidate
        result["prediction_sha256"]["deterministic_pair"] = hashlib.sha256(
            candidate.encode()
        ).hexdigest()
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        with self.assertRaisesRegex(ValueError, "country monotonicity"):
            validate_result(result)

    def test_forward_ast_has_no_privileged_capability(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24642_deterministic_pair_runtime.py",
            ROOT / "src/deepwide_agent/v24642_ror_external_contract.py",
            ROOT / "scripts/run_v24642_ror_task.py",
            ROOT / "scripts/run_v24642_deterministic_pair.py",
            ROOT / "scripts/audit_v24642_deterministic_pair_forward.py",
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
            self.assertNotIn("EVALUATOR_PROTOCOL", text)
        runtime = paths[0].read_text(encoding="utf-8")
        self.assertNotIn("Path(", runtime)
        self.assertNotIn("subprocess", runtime)
        self.assertNotIn("open(", runtime)


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from deepwide_agent.v24642_ror_external_evaluator import (
            evaluate_frozen_rows,
            evaluate_prediction,
            gold_rows,
        )

        cls.evaluate_frozen_rows = staticmethod(evaluate_frozen_rows)
        cls.evaluate_prediction = staticmethod(evaluate_prediction)
        cls.gold = gold_rows(
            (ROOT / "evaluation/v24642_ror_gold_v1.csv").read_text(encoding="utf-8")
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
        self.assertEqual(self.evaluate_prediction(exact, rows)["exact_table_success"], 1)

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
                        "deterministic_pair": exact,
                    },
                }
            )
        value = self.evaluate_frozen_rows(predictions, self.gold)
        self.assertTrue(value["gate_passed"])
        self.assertEqual(
            value["candidate_minus_baseline"]["exact_table_successes"], 12
        )
        self.assertGreaterEqual(value["candidate_minus_baseline"]["item_f1"], 0)


if __name__ == "__main__":
    unittest.main()
