from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25012_attested_detail_external_contract as prior12  # noqa: E402
from deepwide_agent import v25018_multi_identity_external_contract as target  # noqa: E402
from scripts import control_v25018_multi_identity_external as controller  # noqa: E402
from scripts import evaluate_v25018_multi_identity_external as evaluator  # noqa: E402
from scripts import run_v25018_multi_identity_external as runner  # noqa: E402


def content_free_rows(*, advantage_tasks: int = 8) -> list[dict]:
    rows: list[dict] = []
    for index, order in enumerate(target.arm_order_vector()):
        advantage = index < advantage_tasks
        control_distinct = 1 if advantage else 2
        candidate_distinct = 3 if advantage else 2
        gain = candidate_distinct - control_distinct
        arm_metrics = {}
        for arm in target.ARMS:
            distinct = (
                candidate_distinct if arm == target.CANDIDATE_ARM else control_distinct
            )
            arm_metrics[arm] = {
                "planned_queries": 4,
                "executed_queries": 4,
                "logical_fetch_attempts": 10,
                "usable_pages": 10,
                "second_wave_search_prefix_urls": 1,
                "second_wave_visible_link_urls": 3,
                "second_wave_bound_visible_links": distinct,
                "second_wave_target_bound_projected_pages": distinct,
                "second_wave_target_bound_records": distinct,
                "evidence_characters": 5000,
                "synthesis_attempted": True,
                "model_success": True,
                "normalizer_status": "exact",
            }
        parent = {
            "opaque_id": target.task_vector()[index]["opaque_id"],
            "content_free_receipt": {
                "visible_link_strategy_eligible": True,
                "selection_changed": advantage,
                "shared_first_wave_completed": True,
                "shared_second_wave_completed": True,
                "physical_query_count": 4,
                "physical_fetch_count": 14,
                "first_synthesis_arm": order[0],
                "model_logical_call_count": 3,
                "bound_visible_link_gain": gain,
                "candidate_target_bound_projected_page_gain": gain,
                "candidate_target_bound_record_gain": gain,
                "target_bound_record_mechanism_engaged": advantage,
                "arm_metrics": arm_metrics,
            },
            "model_success": {arm: True for arm in target.ARMS},
            "evidence_characters": {arm: 5000 for arm in target.ARMS},
            "prediction_changed": advantage,
            "predictions": {arm: "table" for arm in target.ARMS},
        }
        runtime_result = {
            "parent_result": parent,
            "distinct_identity_selection_receipt": {
                "strategy_eligible": True,
                "selection_changed": int(advantage),
                "new_distinct_identity_gain": gain,
                "control_new_distinct_identity_count": control_distinct,
                "candidate_new_distinct_identity_count": candidate_distinct,
            },
        }
        rows.append(
            {
                "runtime_result": runtime_result,
                "executed_order_receipt": {
                    "task_ordinal": index + 1,
                    "requested_arm_order": order,
                    "executed_synthesis_order": order,
                    "both_arms_synthesis_attempted": True,
                    "executed_order_complete": True,
                    "executed_order_matches_frozen": True,
                },
            }
        )
    return rows


class MultiIdentityExternalContractTests(unittest.TestCase):
    def test_population_is_fresh_fixed_grouped_and_label_blind(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(target.TLD_COHORT), 80)
        self.assertEqual(len(set(target.TLD_COHORT)), 80)
        self.assertFalse(set(target.TLD_COHORT) & target.HISTORICAL_TLD_COHORT)
        self.assertFalse(set(target.TLD_COHORT) & set(prior12.TLD_COHORT))
        self.assertEqual(len(target.identity_groups()), 20)
        self.assertTrue(all(len(group) == 4 for group in target.identity_groups()))
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(
            all(target.IANA_DETAIL_PREFIX not in task["question"] for task in tasks)
        )
        self.assertTrue(
            all(
                target.projector.visible_identities(task["question"]) == group
                for task, group in zip(tasks, target.identity_groups(), strict=True)
            )
        )

    def test_arm_order_is_exactly_balanced_and_bound(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(len(orders), 20)
        self.assertEqual(
            sum(order[0] == target.CANDIDATE_ARM for order in orders), 10
        )
        self.assertTrue(all(set(order) == set(target.ARMS) for order in orders))

    def test_per_arm_hard_budgets_and_public220_closure(self) -> None:
        self.assertEqual(target.LIMITS["wall_seconds"], 240)
        self.assertEqual(target.LIMITS["search_queries"], 4)
        self.assertEqual(target.LIMITS["fetch_targets"], 10)
        self.assertEqual(target.LIMITS["model_calls"], 3)
        self.assertEqual(target.LIMITS["evidence_chars"], 60_000)
        source = target.source_policy()
        self.assertEqual(
            source["paired_physical_query_fetch_caps"],
            {"queries": 4, "fetches": 14},
        )
        self.assertFalse(source["entropy_or_information_gain_assigns_credit_or_routes"])
        self.assertFalse(source["public_deepwidebench_exact220_launch_authorized"])

    def test_mechanism_gate_is_strict_and_execution_order_is_explicit(self) -> None:
        gate = target.mechanism_gate()
        self.assertEqual(gate["terminal_tasks"], 20)
        self.assertEqual(gate["minimum_selection_changed_tasks"], 8)
        self.assertEqual(gate["minimum_total_new_distinct_identity_gain"], 16)
        self.assertEqual(gate["minimum_prediction_changed_tasks"], 6)
        self.assertTrue(
            gate["executed_arm_order_complete_and_matches_frozen_vector"]
        )
        self.assertTrue(gate["all_tasks_plan_exactly_four_queries_per_arm"])
        self.assertTrue(gate["all_tasks_execute_exactly_four_queries_per_arm"])

    def test_protocol_roundtrip_and_resealed_tamper_rejection(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        self.assertEqual(
            target.validate_protocol(ROOT, protocol, tracked=False), protocol
        )
        self.assertEqual(protocol["population"]["selected_visible_identities"], 80)
        self.assertFalse(protocol["authorization"]["one_external_forward"])

        for path, value in (
            (("mechanism_gate_before_evaluator", "minimum_prediction_changed_tasks"), 1),
            (("population", "official_detail_endpoint_vector_sha256"), "0" * 64),
            (("execution", "executor_concurrency"), 1),
        ):
            changed = copy.deepcopy(protocol)
            changed[path[0]][path[1]] = value
            changed.pop("protocol_payload_sha256")
            changed["protocol_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                target.validate_protocol(ROOT, changed, tracked=False)

        extra = copy.deepcopy(protocol)
        extra["authorization"]["unexpected_authority"] = True
        extra.pop("protocol_payload_sha256")
        extra["protocol_payload_sha256"] = target.payload_sha256(extra)
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, extra, tracked=False)

    def test_executed_order_receipt_records_missing_second_arm(self) -> None:
        order = target.arm_order_vector()[0]
        result = {
            "parent_result": {
                "opaque_id": target.task_vector()[0]["opaque_id"],
                "content_free_receipt": {
                    "first_synthesis_arm": order[0],
                    "arm_metrics": {
                        order[0]: {"synthesis_attempted": True},
                        order[1]: {"synthesis_attempted": False},
                    },
                },
            }
        }
        with mock.patch.object(
            target.runtime, "validate_result", side_effect=lambda value: value
        ):
            receipt = target._execution_receipt(
                task_ordinal=1, requested_order=order, result=result
            )
        self.assertEqual(receipt["executed_synthesis_order"], [order[0]])
        self.assertFalse(receipt["both_arms_synthesis_attempted"])
        self.assertFalse(receipt["executed_order_complete"])
        self.assertFalse(receipt["executed_order_matches_frozen"])

    def test_mechanism_gate_go_and_order_or_coverage_no_go(self) -> None:
        rows = content_free_rows()
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            value = controller._mechanism(rows, target.mechanism_gate())
        self.assertTrue(value["passed"])
        self.assertEqual(value["total_new_distinct_identity_gain"], 16)
        self.assertEqual(value["candidate_new_distinct_identity_count"], 48)
        self.assertEqual(value["control_new_distinct_identity_count"], 32)

        missing_order = copy.deepcopy(rows)
        missing_order[0]["executed_order_receipt"]["executed_order_complete"] = False
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            rejected = controller._mechanism(missing_order, target.mechanism_gate())
        self.assertFalse(rejected["passed"])

        low_coverage = content_free_rows(advantage_tasks=7)
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            rejected = controller._mechanism(low_coverage, target.mechanism_gate())
        self.assertFalse(rejected["passed"])

    def test_runner_aggregate_matches_content_free_rows(self) -> None:
        rows = content_free_rows()
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            value = runner._aggregate(rows)
        self.assertEqual(value["terminal_tasks"], 20)
        self.assertEqual(value["executed_order_complete_tasks"], 20)
        self.assertEqual(value["executed_order_matches_frozen_tasks"], 20)
        self.assertEqual(value["total_new_distinct_identity_gain"], 16)
        self.assertEqual(value["tasks_with_positive_distinct_identity_gain"], 8)
        self.assertEqual(value["prediction_changed_tasks"], 8)
        self.assertTrue(value["all_task_evidence_character_counts_equal_between_arms"])

    def test_four_row_evaluator_exact_order_and_missing_gold(self) -> None:
        group = target.identity_groups()[0]
        gold = {
            tld: {
                "Domain": tld,
                "Sponsoring Organisation": f"Registry {index}",
                "Registration date": f"201{index}-01-02",
                "Record last updated": f"202{index}-07-08",
            }
            for index, tld in enumerate(group, 1)
        }
        prediction = "\n".join(
            (
                "| Domain | Sponsoring Organisation | Registration date | Record last updated |",
                "|---|---|---|---|",
                *(
                    f"| {tld} | {gold[tld]['Sponsoring Organisation']} | "
                    f"{gold[tld]['Registration date']} | {gold[tld]['Record last updated']} |"
                    for tld in group
                ),
            )
        )
        metrics = evaluator.evaluate_prediction(prediction, group, gold)
        self.assertEqual(metrics["exact_table_success"], 1)
        self.assertEqual(metrics["item_f1"], 1.0)

        reversed_prediction = "\n".join(
            prediction.splitlines()[:2] + list(reversed(prediction.splitlines()[2:]))
        )
        self.assertEqual(
            evaluator.evaluate_prediction(reversed_prediction, group, gold)[
                "exact_table_success"
            ],
            0,
        )
        missing = dict(gold)
        missing.pop(group[-1])
        self.assertEqual(
            evaluator.evaluate_prediction(prediction, group, missing)[
                "exact_table_success"
            ],
            0,
        )

    def test_missing_gold_task_is_fixed_denominator_zero(self) -> None:
        rows = []
        for index, task in enumerate(target.task_vector()):
            rows.append(
                {
                    "runtime_result": {
                        "parent_result": {
                            "opaque_id": task["opaque_id"],
                            "predictions": {arm: "| invalid |" for arm in target.ARMS},
                            "model_success": {arm: True for arm in target.ARMS},
                        }
                    },
                    "executed_order_receipt": {"task_ordinal": index + 1},
                }
            )
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            value = evaluator.evaluate_rows(rows, {})
        for arm in target.ARMS:
            self.assertEqual(value["arms"][arm]["tasks"], 20)
            self.assertEqual(value["arms"][arm]["rows"], 80)
            self.assertEqual(
                value["arms"][arm]["evaluator_invalid_tasks_failure_as_zero"],
                20,
            )
            self.assertEqual(value["arms"][arm]["exact_table_successes"], 0)

    def test_evaluator_counts_fallback_per_arm(self) -> None:
        rows = []
        for index, task in enumerate(target.task_vector()):
            success = {arm: True for arm in target.ARMS}
            if index == 0:
                success[target.CANDIDATE_ARM] = False
            rows.append(
                {
                    "runtime_result": {
                        "parent_result": {
                            "opaque_id": task["opaque_id"],
                            "predictions": {
                                arm: "| invalid |" for arm in target.ARMS
                            },
                            "model_success": success,
                        }
                    },
                    "executed_order_receipt": {"task_ordinal": index + 1},
                }
            )
        with mock.patch.object(
            target, "validate_task_result", side_effect=lambda value: value
        ):
            value = evaluator.evaluate_rows(rows, {})
        self.assertEqual(
            value["arms"][target.CONTROL_ARM]["fallback_tables"], 0
        )
        self.assertEqual(
            value["arms"][target.CANDIDATE_ARM]["fallback_tables"], 1
        )

    def test_quality_gate_rejects_candidate_fallback_increase(self) -> None:
        arm = {
            "evaluator_invalid_tasks_failure_as_zero": 0,
            "fallback_tables": 0,
        }
        metrics = {
            "arms": {
                target.CONTROL_ARM: dict(arm),
                target.CANDIDATE_ARM: {**arm, "fallback_tables": 1},
            },
            f"{target.CANDIDATE_ARM}_minus_{target.CONTROL_ARM}": {
                "exact_table_successes": 1,
                "entity_recall": 0.0,
                "row_f1": 0.0,
                "item_f1": 0.0,
                "column_f1": 0.0,
                "composite": 0.0,
            },
        }
        self.assertFalse(
            evaluator.quality_gate_passed(metrics, mechanism_passed=True)
        )
        metrics["arms"][target.CANDIDATE_ARM]["fallback_tables"] = 0
        self.assertTrue(
            evaluator.quality_gate_passed(metrics, mechanism_passed=True)
        )

    def test_forward_sources_do_not_import_benchmark_or_evaluator(self) -> None:
        for relative in (
            target.PROJECTOR,
            target.FETCH,
            target.SELECTOR,
            target.RUNTIME,
            target.HELPER,
            target.RUNNER,
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name.casefold() for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append((node.module or "").casefold())
            self.assertFalse(
                any(
                    "deepwidebench" in name or "evaluate_v25018" in name
                    for name in imports
                )
            )

    def test_future_surfaces_are_distinct_create_only_and_no_resume(self) -> None:
        paths = {
            target.PREAUDIT,
            target.EXECUTION_START,
            target.FORWARD_RESULT,
            target.FORWARD_AUDIT,
            target.EVALUATOR_PROTOCOL,
            target.RESULT,
            target.POSTAUDIT,
            target.OUTPUT_ROOT,
        }
        self.assertEqual(len(paths), 8)
        runner_source = (ROOT / target.RUNNER).read_text(encoding="utf-8")
        evaluator_source = (ROOT / target.EVALUATOR).read_text(encoding="utf-8")
        self.assertIn("os.O_EXCL", runner_source)
        self.assertIn("os.O_EXCL", evaluator_source)
        self.assertNotIn('"--resume"', runner_source.casefold())
        self.assertNotIn("def resume", runner_source.casefold())
        self.assertNotIn("def retry", runner_source.casefold())


if __name__ == "__main__":
    unittest.main()
