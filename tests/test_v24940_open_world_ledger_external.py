from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import evaluate_v24940_open_world_ledger_external as evaluator  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as runner  # noqa: E402
from scripts import run_v24940_open_world_ledger_external_task as task_runner  # noqa: E402


def catalog_blob(count: int = 260) -> bytes:
    records = [
        {"id": f"X{index:02X}"[-3:], "name": f"Country {index:03d}", "region": {"id": "R"}}
        for index in range(count)
    ]
    # Use three-character stable pseudo ISO3 values.
    for index, record in enumerate(records):
        record["id"] = f"{chr(65 + index // 100)}{index % 100:02d}"
    return json.dumps([{}, records]).encode()


def target_blob(count: int = 260) -> bytes:
    records = []
    for index in range(count):
        iso3 = f"{chr(65 + index // 100)}{index % 100:02d}"
        records.append(
            {
                "country": {"value": f"Country {index:03d}"},
                "countryiso3code": iso3,
                "value": str(10 + index / 10),
            }
        )
    return json.dumps([{}, records]).encode()


class V24940OpenWorldLedgerExternalTests(unittest.TestCase):
    def test_target_is_fixed_and_absent_from_declared_development_set(self) -> None:
        self.assertEqual(contract.TARGET_KEYS, ("SP.DYN.IMRT.IN@2022",))
        self.assertTrue(set(contract.TARGET_KEYS).isdisjoint(contract.DEVELOPMENT_TARGET_KEYS))

    def test_visible_task_contains_schema_and_cohort_but_no_row_identities(self) -> None:
        cohorts = runner._cohorts()
        columns = " | ".join(contract.visible_columns())
        tasks = []
        for index, cohort in enumerate(cohorts):
            tasks.append(
                {
                    "opaque_id": "task_" + hashlib.sha256(str(index).encode()).hexdigest()[:24],
                    "question": (
                        f"Include every record whose Cohort is {cohort}. "
                        "Do not include other cohorts.\nColumn names: "
                        + columns
                        + f"\nThe visible Cohort predicate is {cohort}."
                    ),
                }
            )
        validated = contract.validate_task_vector(tasks)
        self.assertEqual(len(validated), contract.SELECTED_COUNT)
        self.assertTrue(all("<ENTITIES>" not in row["question"] for row in validated))

    def test_cohort_vector_is_deterministic_and_unique(self) -> None:
        self.assertEqual(runner._cohorts(), runner._cohorts())
        self.assertEqual(len(set(runner._cohorts())), contract.SELECTED_COUNT)

    def test_parse_target_requires_public_capacity(self) -> None:
        _page, values = runner.parse_target(
            target_blob(), dict(contract.TARGETS[0]), contract.TARGET_URLS[0]
        )
        self.assertEqual(len(values), 260)
        with self.assertRaises(RuntimeError):
            runner.parse_target(
                target_blob(100), dict(contract.TARGETS[0]), contract.TARGET_URLS[0]
            )

    def test_build_snapshot_has_disjoint_targets_and_fixed_shared_distractors(self) -> None:
        bundle, tasks, freeze = runner.build_snapshot(catalog_blob(), [target_blob()])
        self.assertEqual(len(bundle["pages"]), contract.SELECTED_COUNT)
        self.assertEqual(len(tasks), contract.SELECTED_COUNT)
        self.assertEqual(freeze["selected_target_entities"], contract.SELECTED_ENTITY_COUNT)
        gold = evaluator.build_gold(tasks, bundle)
        identities = [
            row["Country"] for values in gold.values() for row in values
        ]
        self.assertEqual(len(identities), contract.SELECTED_ENTITY_COUNT)
        self.assertEqual(len(set(identities)), contract.SELECTED_ENTITY_COUNT)

    def test_candidate_projection_exposes_all_target_rows_on_synthetic_page(self) -> None:
        bundle, tasks, _freeze = runner.build_snapshot(catalog_blob(), [target_blob()])
        pages = [bundle["pages"][0]]
        value = task_runner.build_projections(tasks[0]["question"], pages)
        parent = value["parent_30k"]
        candidate = value["target_value_30k"]
        receipt = candidate["receipt"]
        self.assertNotEqual(parent["projection"], candidate["projection"])
        self.assertEqual(receipt["discovered_row_key_count"], contract.PAGE_ROWS_PER_TASK)
        self.assertEqual(
            receipt["admissible_bound_observation_count"],
            contract.PAGE_ROWS_PER_TASK * (len(contract.visible_columns()) - 1),
        )
        cohort = contract.parse_visible_cohort(tasks[0]["question"])
        target_rows = [
            row["Country"]
            for row in evaluator._source_rows(pages[0])
            if row["Cohort"] == cohort
        ]
        self.assertTrue(all(row in candidate["projection"] for row in target_rows))

    def test_evaluator_exact_and_partial_metrics(self) -> None:
        columns = contract.visible_columns()
        gold = [
            {columns[0]: "Alpha", columns[1]: "C01", columns[2]: "ALP", columns[3]: "12.3"},
            {columns[0]: "Beta", columns[1]: "C01", columns[2]: "BET", columns[3]: "13.4"},
        ]
        table = "| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) + " |\n"
        table += "\n".join("| " + " | ".join(row[column] for column in columns) + " |" for row in gold)
        self.assertEqual(evaluator.evaluate_prediction(table, gold)["exact_table_success"], 1)
        self.assertEqual(evaluator.evaluate_prediction("bad", gold)["exact_table_success"], 0)

    def test_task_arm_order_is_counterbalanced_and_deterministic(self) -> None:
        values = [contract.arm_order("task_" + f"{index:024x}") for index in range(24)]
        self.assertEqual(values, [contract.arm_order("task_" + f"{index:024x}") for index in range(24)])
        self.assertEqual(set(values), {contract.ARMS, contract.ARMS[::-1]})

    def test_matched_cost_prompt_and_one_attempt_are_frozen(self) -> None:
        self.assertEqual(contract.MODEL["attempts_per_arm"], 1)
        self.assertIn("supplied frozen public-derived page", task_runner._prompt("q", "e"))
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)

    def test_runtime_boundary_and_evaluator_separation(self) -> None:
        self.assertNotIn(contract.EVALUATOR, contract.RUNTIME_SOURCES)
        self.assertIn(contract.CHILD, contract.RUNTIME_SOURCES)
        self.assertEqual(contract.parse_visible_countries("C01 C01"), [])

    def test_runtime_sources_have_no_privileged_field_reads_or_secrets(self) -> None:
        privileged = {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
        for relative in contract.RUNTIME_SOURCES:
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            hits = []
            for node in ast.walk(tree):
                key = None
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"get", "pop", "setdefault"} and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    key = node.args[0].value.casefold()
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    key = node.slice.value.casefold()
                if key in privileged:
                    hits.append((node.lineno, key))
            self.assertEqual(hits, [], str(relative))
            self.assertNotIn("tvly-dev-", source)
            self.assertNotIn("ghp_", source)

    def test_contract_rejects_duplicate_cohort_and_bad_runtime_keys(self) -> None:
        cohort = runner._cohorts()[0]
        question = (
            f"Include every record whose Cohort is {cohort}. Do not include other cohorts.\n"
            "Column names: " + " | ".join(contract.visible_columns()) + f"\nCohort is {cohort}."
        )
        tasks = [
            {"opaque_id": "task_" + f"{index:024x}", "question": question}
            for index in range(contract.SELECTED_COUNT)
        ]
        with self.assertRaises(ValueError):
            contract.validate_task_vector(tasks)
        tasks[0]["extra"] = "bad"
        with self.assertRaises(ValueError):
            contract.validate_task_vector(tasks)


if __name__ == "__main__":
    unittest.main()
