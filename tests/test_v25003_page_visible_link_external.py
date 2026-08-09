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

from deepwide_agent import v25000_identity_authority_selection_external_contract as prior00  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v25003_page_visible_link_external_contract as target,
)
from scripts import (  # noqa: E402
    control_v25003_page_visible_link_external as controller,
)
from scripts import (  # noqa: E402
    run_v25003_page_visible_link_external as runner,
)


def content_free_rows() -> list[dict]:
    rows: list[dict] = []
    for index, order in enumerate(target.arm_order_vector()):
        advantage = index < 8
        arm_metrics = {}
        for arm in target.ARMS:
            candidate = arm == target.CANDIDATE_ARM
            gain = int(candidate and advantage)
            arm_metrics[arm] = {
                "planned_queries": 4,
                "executed_queries": 4,
                "logical_fetch_attempts": 10,
                "usable_pages": 10,
                "second_wave_search_prefix_urls": 1,
                "second_wave_visible_link_urls": 3,
                "second_wave_bound_visible_links": gain,
                "second_wave_target_bound_projected_pages": gain,
                "second_wave_target_bound_records": gain,
                "evidence_characters": 5000,
                "synthesis_attempted": True,
                "model_success": True,
                "normalizer_status": "exact",
            }
        rows.append(
            {
                "content_free_receipt": {
                    "visible_link_strategy_eligible": True,
                    "selection_changed": advantage,
                    "shared_first_wave_completed": True,
                    "shared_second_wave_completed": True,
                    "physical_query_count": 4,
                    "physical_fetch_count": 11 if advantage else 10,
                    "first_synthesis_arm": order[0],
                    "model_logical_call_count": 3,
                    "bound_visible_link_gain": int(advantage),
                    "candidate_target_bound_projected_page_gain": int(advantage),
                    "candidate_target_bound_record_gain": int(advantage),
                    "target_bound_record_mechanism_engaged": advantage,
                    "arm_metrics": arm_metrics,
                },
                "model_success": {arm: True for arm in target.ARMS},
                "evidence_characters": {arm: 5000 for arm in target.ARMS},
                "prediction_changed": advantage,
            }
        )
    return rows


class PageVisibleLinkExternalContractTests(unittest.TestCase):
    def test_population_is_fresh_fixed_unique_and_label_blind(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertFalse(set(target.TLD_COHORT).intersection(prior00.TLD_COHORT))
        self.assertFalse(
            set(target.TLD_COHORT).intersection(prior00.HISTORICAL_TLD_COHORT)
        )
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all(target.IANA_URL not in row["question"] for row in tasks))

    def test_arm_order_is_exactly_balanced_and_bound(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(len(orders), 20)
        self.assertEqual(
            sum(order[0] == target.CANDIDATE_ARM for order in orders), 10
        )
        self.assertTrue(all(set(order) == set(target.ARMS) for order in orders))

    def test_per_arm_hard_budgets_match_production(self) -> None:
        self.assertEqual(
            target.LIMITS,
            {
                "wall_seconds": 240,
                "model_calls": 3,
                "search_queries": 4,
                "fetch_targets": 10,
                "search_results_per_query": 3,
                "evidence_chars": 60000,
                "page_chars": 5000,
                "plan_output_tokens": 4000,
                "synthesis_output_tokens": 30000,
                "repair_output_tokens": 12000,
            },
        )
        source = target.source_policy()
        self.assertEqual(
            source["per_arm_logical_query_fetch_caps"],
            {"queries": 4, "fetches": 10},
        )
        self.assertEqual(
            source["paired_physical_query_fetch_caps"],
            {"queries": 4, "fetches": 14},
        )
        self.assertTrue(
            source["external_gate_not_a_production_latency_or_throughput_measurement"]
        )

    def test_mechanism_gate_is_strict_and_quality_remains_closed(self) -> None:
        gate = target.mechanism_gate()
        self.assertEqual(gate["terminal_tasks"], 20)
        self.assertEqual(gate["minimum_visible_link_strategy_eligible_tasks"], 12)
        self.assertEqual(gate["shared_first_wave_completed_tasks"], 20)
        self.assertEqual(gate["shared_second_wave_completed_tasks"], 20)
        self.assertEqual(gate["minimum_both_arms_model_success_tasks"], 18)
        self.assertEqual(gate["minimum_selection_changed_tasks"], 8)
        self.assertEqual(gate["minimum_total_bound_visible_link_gain"], 8)
        self.assertEqual(
            gate["minimum_tasks_with_positive_target_bound_projected_page_gain"], 8
        )
        self.assertEqual(
            gate["minimum_tasks_with_positive_target_bound_record_gain"], 8
        )
        self.assertEqual(
            gate["minimum_target_bound_record_mechanism_engaged_tasks"], 8
        )
        self.assertEqual(gate["minimum_prediction_changed_tasks"], 4)
        source = target.source_policy()
        self.assertFalse(source["entropy_or_information_gain_assigns_credit_or_routes"])
        self.assertFalse(source["public_deepwidebench_exact220_launch_authorized"])

    def test_forward_sources_do_not_import_benchmark_or_evaluator(self) -> None:
        for relative in (
            target.PROJECTOR,
            target.FETCH,
            target.PARENT_SELECTOR,
            target.PARENT_RUNTIME,
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
                    "deepwidebench" in name or "evaluate_v25003" in name
                    for name in imports
                )
            )

    def test_future_surfaces_are_distinct_and_create_only(self) -> None:
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
        evaluator = (ROOT / target.EVALUATOR).read_text(encoding="utf-8")
        self.assertIn("os.O_EXCL", runner_source)
        self.assertIn("os.O_EXCL", evaluator)
        self.assertNotIn('"--resume"', runner_source.casefold())
        self.assertNotIn("def resume", runner_source.casefold())
        self.assertNotIn("def retry", runner_source.casefold())

    def test_protocol_roundtrip_before_files_are_tracked(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        checked = target.validate_protocol(ROOT, protocol, tracked=False)
        self.assertEqual(checked, protocol)
        self.assertEqual(checked["population"]["selected_tasks"], 20)
        self.assertFalse(checked["authorization"]["one_external_forward"])
        self.assertEqual(
            checked["mechanism_gate_before_evaluator"], target.mechanism_gate()
        )

    def test_protocol_resealed_tamper_is_rejected(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        tampered = copy.deepcopy(protocol)
        tampered["mechanism_gate_before_evaluator"][
            "minimum_prediction_changed_tasks"
        ] = 1
        tampered.pop("protocol_payload_sha256")
        tampered["protocol_payload_sha256"] = target.payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_protocol(ROOT, tampered, tracked=False)

        endpoint = copy.deepcopy(protocol)
        endpoint["population"]["official_gold_endpoint_sha256"] = "0" * 64
        endpoint.pop("protocol_payload_sha256")
        endpoint["protocol_payload_sha256"] = target.payload_sha256(endpoint)
        with self.assertRaises(ValueError):
            target.validate_protocol(ROOT, endpoint, tracked=False)

        extra = copy.deepcopy(protocol)
        extra["authorization"]["unexpected_authority"] = True
        extra.pop("protocol_payload_sha256")
        extra["protocol_payload_sha256"] = target.payload_sha256(extra)
        with self.assertRaises(ValueError):
            target.validate_protocol(ROOT, extra, tracked=False)

    def test_runner_has_shared_plan_two_distinct_search_clients_and_no_gold(self) -> None:
        source = (ROOT / target.RUNNER).read_text(encoding="utf-8")
        self.assertIn("runtime.run_paired_task", source)
        self.assertIn("for phase in contract.PHASES", source)
        self.assertIn(
            "ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY)", source
        )
        self.assertNotIn("contract.IANA_URL", source)
        self.assertNotIn("POSTFREEZE_GOLD", source)

    def test_mechanism_gate_go_and_url_without_record_no_go_boundaries(self) -> None:
        rows = content_free_rows()
        with mock.patch.object(
            controller.runtime, "validate_result", side_effect=lambda row: row
        ):
            value = controller._mechanism(rows, target.mechanism_gate())
            self.assertTrue(value["passed"])
            self.assertEqual(value["selection_changed_tasks"], 8)
            self.assertEqual(value["total_bound_visible_link_gain"], 8)
            self.assertEqual(
                value["target_bound_record_mechanism_engaged_tasks"], 8
            )

            no_records = copy.deepcopy(rows)
            for row in no_records[:8]:
                candidate = row["content_free_receipt"]["arm_metrics"][
                    target.CANDIDATE_ARM
                ]
                candidate["second_wave_target_bound_projected_pages"] = 0
                candidate["second_wave_target_bound_records"] = 0
                row["content_free_receipt"][
                    "candidate_target_bound_projected_page_gain"
                ] = 0
                row["content_free_receipt"]["candidate_target_bound_record_gain"] = 0
                row["content_free_receipt"][
                    "target_bound_record_mechanism_engaged"
                ] = False
            rejected = controller._mechanism(no_records, target.mechanism_gate())
            self.assertFalse(rejected["passed"])

            negative = copy.deepcopy(rows)
            first = negative[0]["content_free_receipt"]
            first["arm_metrics"][target.CONTROL_ARM][
                "second_wave_target_bound_records"
            ] = 2
            first["arm_metrics"][target.CANDIDATE_ARM][
                "second_wave_target_bound_records"
            ] = 1
            first["candidate_target_bound_record_gain"] = -1
            first["target_bound_record_mechanism_engaged"] = False
            rejected = controller._mechanism(negative, target.mechanism_gate())
            self.assertFalse(rejected["passed"])

    def test_runner_aggregate_matches_content_free_rows(self) -> None:
        value = runner._aggregate(content_free_rows())
        self.assertEqual(value["terminal_tasks"], 20)
        self.assertEqual(value["visible_link_strategy_eligible_tasks"], 20)
        self.assertEqual(value["selection_changed_tasks"], 8)
        self.assertEqual(value["shared_first_wave_completed_tasks"], 20)
        self.assertEqual(value["shared_second_wave_completed_tasks"], 20)
        self.assertTrue(value["all_tasks_execute_exactly_four_physical_queries"])
        self.assertTrue(value["all_tasks_fetch_at_most_fourteen_physical_pages"])
        self.assertEqual(value["both_arms_model_success_tasks"], 20)
        self.assertEqual(value["prediction_changed_tasks"], 8)
        self.assertEqual(value["total_bound_visible_link_gain"], 8)
        self.assertEqual(
            value["tasks_with_positive_target_bound_record_gain"], 8
        )
        self.assertEqual(
            value["arms"][target.CANDIDATE_ARM][
                "second_wave_target_bound_records"
            ],
            8,
        )


if __name__ == "__main__":
    unittest.main()
