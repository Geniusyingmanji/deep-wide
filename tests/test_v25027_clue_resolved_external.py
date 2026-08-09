from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25026_resolved_schema_reachability as reachability  # noqa: E402
from deepwide_agent import v25027_clue_resolved_external_contract as target  # noqa: E402
from scripts import control_v25027_clue_resolved_external as controller  # noqa: E402
from scripts import run_v25027_clue_resolved_external as runner  # noqa: E402


def resolved_receipt(advantage: bool = True) -> dict:
    question = (
        "Identify the jurisdiction whose capital is Visible City. Return a table. "
        "Column names: Domain, Type, TLD Manager."
    )
    queries = {
        reachability.SHARED_PHASE: ["Visible City currency", "capital clue"],
        reachability.CONTROL_ARM: ["root database", "official domain list"],
        reachability.CANDIDATE_ARM: [
            "Resolvedland country code domain",
            "Resolvedland Domain Type TLD Manager",
        ],
    }
    pages = {
        reachability.SHARED_PHASE: [
            {"title": "Profile", "content": "Resolvedland capital Visible City"}
        ],
        reachability.CONTROL_ARM: [
            {"title": "Root", "content": "Domain Type TLD Manager generic index"}
        ],
        reachability.CANDIDATE_ARM: [
            {
                "title": "Resolvedland delegation",
                "content": (
                    "Resolvedland country-code Domain Type TLD Manager Registry"
                    if advantage else "unrelated text"
                ),
            }
        ],
    }
    return reachability.build_receipt(question, queries, pages)


def content_free_rows(*, advantages: int = 6, changes: int = 6) -> list[dict]:
    rows: list[dict] = []
    for index, order in enumerate(target.arm_order_vector()):
        metrics = {
            arm: {
                "executed_queries": 4,
                "fetch_attempts": 8,
                "usable_pages": 7,
                "query_local_results": 1,
                "retained_records": 0,
                "evidence_characters": 30000,
            }
            for arm in target.ARMS
        }
        rows.append(
            {
                "content_free_receipt": {
                    "refinement_model_call_attempted": True,
                    "refinement_strategy_applied": index < 12,
                    "query_vectors_differ_only_in_second_wave": index < 12,
                    "shared_prefix_byte_equal_between_arms": True,
                    "physical_query_count": 6,
                    "physical_fetch_count": 14,
                    "model_logical_call_count": 4,
                    "model_provider_request_count": 4,
                    "first_delta_arm": order[0],
                    "arm_metrics": metrics,
                    "resolved_schema_reachability_receipt": resolved_receipt(
                        index < advantages
                    ),
                },
                "model_success": {arm: True for arm in target.ARMS},
                "prediction_changed": index < changes,
            }
        )
    return rows


class ClueResolvedExternalTests(unittest.TestCase):
    def test_public_population_is_fixed_unique_and_mapping_free(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertEqual(len(set(target.CLUES)), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all("<DOMAIN>" not in row["question"] for row in tasks))
        self.assertFalse((ROOT / target.EVALUATOR_MAPPING).exists())

    def test_arm_order_is_exactly_balanced(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(sum(order[0] == target.CANDIDATE_ARM for order in orders), 10)
        self.assertTrue(all(set(order) == set(target.ARMS) for order in orders))

    def test_budget_and_quality_gates_are_strict(self) -> None:
        source = target.source_policy()
        self.assertEqual(
            source["per_arm_logical_model_query_fetch_caps"],
            {"models": 3, "queries": 4, "fetches": 10},
        )
        self.assertEqual(
            source["paired_physical_model_query_fetch_caps"],
            {"models": 4, "queries": 6, "fetches": 14},
        )
        quality = target.quality_gate()
        self.assertTrue(quality["candidate_exact_strictly_greater"])
        self.assertTrue(quality["candidate_composite_strictly_greater"])
        self.assertFalse(source["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_protocol_roundtrip_untracked_and_future_closed(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        self.assertEqual(target.validate_protocol(ROOT, protocol, tracked=False), protocol)
        self.assertFalse(protocol["authorization"]["one_external_forward"])
        self.assertFalse(protocol["population"]["country_tld_or_gold_mapping_module_present_opened_or_hashed"])

    def test_protocol_resealed_gate_tamper_is_rejected(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        changed = copy.deepcopy(protocol)
        changed["mechanism_gate_before_evaluator"]["minimum_prediction_changed_tasks"] = 1
        changed.pop("protocol_payload_sha256")
        changed["protocol_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_protocol(ROOT, changed, tracked=False)

    def test_forward_sources_exclude_mapping_evaluator_and_benchmark(self) -> None:
        self.assertNotIn(target.EVALUATOR_MAPPING, target.FORWARD_SOURCES)
        self.assertNotIn(target.EVALUATOR, target.FORWARD_SOURCES)
        for relative in target.FORWARD_SOURCES:
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(item.name.casefold() for item in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append((node.module or "").casefold())
            self.assertFalse(any("deepwidebench" in name for name in imports))
            self.assertFalse(any("v25027_clue_gold_mapping" in name for name in imports))

    def test_mechanism_go_boundary(self) -> None:
        with mock.patch.object(
            controller.runtime, "validate_result", side_effect=lambda row: row
        ):
            value = controller._mechanism(content_free_rows(), target.mechanism_gate())
        self.assertTrue(value["passed"])
        self.assertEqual(value["candidate_resolved_schema_pages"], 6)
        self.assertEqual(value["prediction_changed_tasks"], 6)

    def test_mechanism_rejects_zero_reachability(self) -> None:
        with mock.patch.object(
            controller.runtime, "validate_result", side_effect=lambda row: row
        ):
            value = controller._mechanism(
                content_free_rows(advantages=0, changes=6), target.mechanism_gate()
            )
        self.assertFalse(value["passed"])

    def test_runner_aggregate_is_content_free(self) -> None:
        value = runner._aggregate(content_free_rows())
        self.assertEqual(value["terminal_tasks"], 20)
        self.assertEqual(value["candidate_resolved_schema_pages"], 6)
        self.assertEqual(value["control_resolved_schema_pages"], 0)
        self.assertEqual(value["prediction_changed_tasks"], 6)

    def test_runner_requires_absent_evaluator_surfaces(self) -> None:
        source = (ROOT / target.RUNNER).read_text(encoding="utf-8")
        self.assertIn("contract.EVALUATOR_MAPPING", source)
        self.assertIn("contract.EVALUATOR", source)
        self.assertIn("runtime.run_paired_task", (ROOT / "scripts/run_v24997_shared_first_wave_external.py").read_text(encoding="utf-8"))
        self.assertNotIn("--resume", source.casefold())


if __name__ == "__main__":
    unittest.main()
