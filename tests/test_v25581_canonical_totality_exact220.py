from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as visible_schema  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25541_visible_output_constraint_contract as constraints  # noqa: E402
from deepwide_agent import v25569_constraint_totality_safe_handoff_runtime as surface  # noqa: E402
from deepwide_agent import v25575_canonical_column_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25581_canonical_totality_exact220_contract as contract  # noqa: E402
from scripts import control_v25581_canonical_totality_exact220 as control  # noqa: E402
from scripts import finalize_v25581_canonical_totality_exact220 as finalizer  # noqa: E402
from scripts import run_v25581_canonical_totality_exact220 as runner  # noqa: E402


class V25581ConstraintExact220Tests(unittest.TestCase):
    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(
            contract.payload_sha256([task["opaque_id"] for task in tasks]),
            "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a",
        )

    def test_schema_total_reachability_is_exact220(self) -> None:
        limits = visible_schema.score.ScoreFirstLimits(**contract.LIMITS)
        counts = {name: 0 for name in visible_schema.SCHEMA_SOURCES}
        for task in contract.task_vector(ROOT):
            plan, _observation, source = visible_schema.projected_plan(
                {}, task["question"], limits
            )
            counts[source] += 1
            self.assertEqual(len(plan["queries"]), 4)
            self.assertGreaterEqual(len(plan["columns"]), 1)
        self.assertEqual(
            counts,
            {
                "exact_visible": 194,
                "expanded_visible": 21,
                "provider_plan": 0,
                "generic_result": 5,
            },
        )

    def test_totality_constraint_parent_authority_is_hash_bound(self) -> None:
        parents = contract.parent_receipts(ROOT, tracked=True)
        self.assertEqual(
            parents["v25580_fresh_canonical_totality_quality_audit"]["sha256"],
            contract.PARENT_QUALITY_AUDIT_SHA256,
        )

    def test_high_concurrency_and_physical_caps_are_fixed(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 40)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(
            contract.PHYSICAL_CAPS,
            {
                "queries_per_task": 4,
                "fetches_per_task": 14,
                "model_forwards_per_task": 3,
            },
        )

    def test_inherited_shells_bind_the_frozen_exact_schema_parser(self) -> None:
        control.configure()
        self.assertIs(control.base.visible_schema, visible_schema.exact_schema)
        runner.configure()
        self.assertIs(runner.base.visible_schema, visible_schema.exact_schema)
        fallback = runner.base._visible_fallback(
            "Return columns exactly: Package | Version | License."
        )
        self.assertIn("| Package | Version | License |", fallback)
        self.assertIn("| Unknown | Unknown | Unknown |", fallback)
        self.assertIs(runner.base.runtime, runtime)
        self.assertIs(
            runner.base._terminal_outer_failure, runner._terminal_outer_failure
        )

    def test_failure_totality_drops_only_incompatible_private_stage(self) -> None:
        task = contract.task_vector(ROOT)[0]
        raw = self._synthetic_failure_row(task)
        raw["content_free_stage_receipt"] = {"old_parent_stage": True}
        raw.pop("result_payload_sha256")
        raw["result_payload_sha256"] = contract.payload_sha256(raw)
        with mock.patch.object(
            runner,
            "_INHERITED_TERMINAL_OUTER_FAILURE",
            return_value=raw,
        ):
            value = runner._terminal_outer_failure(
                task, RuntimeError("x"), 1.0, object(), None, {}
            )
        self.assertIsNone(value["content_free_stage_receipt"])
        unsigned = dict(value)
        seal = unsigned.pop("result_payload_sha256")
        self.assertEqual(seal, contract.payload_sha256(unsigned))

    def test_historical_parent_replay_totality_modes_preserve_all_predictions(self) -> None:
        source = ROOT / (
            "outputs/v25406_grounded_membership_exact220_v1_20260813/"
            "frozen_task_results.jsonl"
        )
        counts = {runtime.CANONICAL_PROJECTION: 0, runtime.BYTE_EXACT_PARENT_HANDOFF: 0}
        preserved = 0
        for line in source.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if not row["runtime_completed"]:
                continue
            task = next(
                task
                for task in contract.task_vector(ROOT)
                if task["opaque_id"] == row["opaque_id"]
            )
            result = surface.build_result(row["runtime_result"], task["question"])
            counts[result["mode"]] += 1
            preserved += int(
                result["predictions"][runtime.CONTROL_ARM]
                == row["runtime_result"]["prediction"]
            )
        self.assertEqual(counts, {runtime.CANONICAL_PROJECTION: 204, runtime.BYTE_EXACT_PARENT_HANDOFF: 5})
        self.assertEqual(preserved, 209)

    def test_totality_row_fields_reject_unsafe_handoff(self) -> None:
        task = contract.task_vector(ROOT)[0]
        raw = self._synthetic_failure_row(task)
        raw["content_free_stage_receipt"] = {"old_parent_stage": True}
        raw.pop("result_payload_sha256")
        raw["result_payload_sha256"] = contract.payload_sha256(raw)
        with mock.patch.object(
            runner,
            "_INHERITED_TERMINAL_OUTER_FAILURE",
            return_value=raw,
        ):
            value = runner._terminal_outer_failure(
                task, RuntimeError("x"), 1.0, object(), None, {}
            )
        self.assertIsNone(value["projection_mode"])
        self.assertFalse(value["unsafe_handoff_present"])
        changed = copy.deepcopy(value)
        changed["unsafe_handoff_present"] = True
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            runner.validate_task_row(changed)

    def test_historical_completed_rows_rebuild_both_totality_modes(self) -> None:
        source = ROOT / (
            "outputs/v25406_grounded_membership_exact220_v1_20260813/"
            "frozen_task_results.jsonl"
        )
        tasks = {task["opaque_id"]: task for task in contract.task_vector(ROOT)}
        observed: dict[str, dict] = {}
        for line in source.read_text(encoding="utf-8").splitlines():
            parent_row = json.loads(line)
            if not parent_row["runtime_completed"]:
                continue
            task = tasks[parent_row["opaque_id"]]
            result = surface.build_result(
                parent_row["runtime_result"], task["question"]
            )
            stage = surface._stage_receipt(
                result, parent_row["content_free_stage_receipt"]
            )
            rebuilt = runner._from_runtime(
                task,
                result,
                stage,
                1.0,
                self._BudgetReplay(parent_row["content_free_budget_receipt"]),
                self._CounterReplay(parent_row["actual_effect_snapshot"]),
                {
                    "replay": self._SearchCounterReplay(
                        parent_row["actual_effect_snapshot"]
                    )
                },
            )
            checked = runner.validate_task_row(rebuilt)
            observed.setdefault(checked["projection_mode"], checked)
            if len(observed) == 2:
                break
        self.assertEqual(
            set(observed),
            {runtime.CANONICAL_PROJECTION, runtime.BYTE_EXACT_PARENT_HANDOFF},
        )
        handoff = observed[runtime.BYTE_EXACT_PARENT_HANDOFF]
        self.assertTrue(handoff["safe_handoff"])
        self.assertFalse(handoff["unsafe_handoff_present"])
        self.assertFalse(handoff["handoff_date_scale_sort_modification_present"])
        self.assertTrue(handoff["parent_prediction_byte_preserved"])

    def test_v25575_frozen_rows_decode_both_successor_schemas(self) -> None:
        source = ROOT / (
            "outputs/v25579_fresh_canonical_totality_v1_20260818/"
            "frozen_task_results.jsonl"
        )
        observed: dict[str, dict] = {}
        for line in source.read_text(encoding="utf-8").splitlines():
            parent_row = json.loads(line)
            if not parent_row["successor_runtime_completed"]:
                continue
            decoded = runner._decode_totality(
                parent_row["runtime_result"],
                parent_row["content_free_stage_receipt"],
            )
            observed.setdefault(parent_row["successor_mode"], decoded)
        self.assertEqual(
            set(observed),
            {"canonical_column_handoff", runtime.CANONICAL_PROJECTION},
        )
        handoff = observed["canonical_column_handoff"]
        self.assertTrue(handoff["canonical_column_handoff"])
        self.assertTrue(handoff["byte_exact_parent_handoff"])
        self.assertTrue(handoff["safe_handoff"])
        ordinary = observed[runtime.CANONICAL_PROJECTION]
        self.assertFalse(ordinary["canonical_column_handoff"])
        self.assertTrue(ordinary["canonical_projection"])

    def test_v25575_both_schemas_cross_the_full_exact220_outer_boundary(self) -> None:
        source = ROOT / (
            "outputs/v25579_fresh_canonical_totality_v1_20260818/"
            "frozen_task_results.jsonl"
        )
        observed: dict[str, dict] = {}
        for line in source.read_text(encoding="utf-8").splitlines():
            source_row = json.loads(line)
            mode = source_row["successor_mode"]
            if mode in observed:
                continue
            effect = source_row["actual_effect_snapshot"]
            model = self._CounterReplayFromAdmitted(effect)
            searches = {"replay": self._SearchReplayFromAdmitted(effect)}
            rebuilt = runner._from_runtime(
                {
                    "opaque_id": source_row["opaque_id"],
                    "question": "Visible synthetic schema-bound question.",
                },
                source_row["runtime_result"],
                source_row["content_free_stage_receipt"],
                1.0,
                self._BudgetReplay(
                    source_row["content_free_stage_receipt"][
                        "outer_physical_budget_receipt"
                    ]
                ),
                model,
                searches,
            )
            observed[mode] = runner.validate_task_row(rebuilt)
        self.assertEqual(
            set(observed),
            {"canonical_column_handoff", runtime.CANONICAL_PROJECTION},
        )
        self.assertTrue(
            observed["canonical_column_handoff"]["canonical_column_handoff"]
        )
        self.assertTrue(
            observed["canonical_column_handoff"]["safe_handoff"]
        )
        self.assertTrue(
            observed[runtime.CANONICAL_PROJECTION]["canonical_projection"]
        )

    def test_watcher_contract_binds_only_healthy_identity_and_absent_history(self) -> None:
        snapshot = contract.watcher_snapshot()
        self.assertEqual(
            snapshot,
            [{
                "pid": 2808901,
                "marker": "scripts/watch_v24215_joint_package_recovery.py",
                "start_ticks": 746680268,
            }],
        )
        self.assertEqual(
            [pid for pid, _marker in contract.EXPECTED_ABSENT_WATCHERS],
            [795336, 3061652, 2889939],
        )

    def test_fixed220_failure_rows_aggregate_without_successor_recursion(self) -> None:
        rows = []
        for task in contract.task_vector(ROOT):
            raw = self._synthetic_failure_row(task)
            raw["content_free_stage_receipt"] = {"old_parent_stage": True}
            raw.pop("result_payload_sha256")
            raw["result_payload_sha256"] = contract.payload_sha256(raw)
            with mock.patch.object(
                runner,
                "_INHERITED_TERMINAL_OUTER_FAILURE",
                return_value=raw,
            ):
                rows.append(
                    runner._terminal_outer_failure(
                        task, RuntimeError("synthetic"), 1.0,
                        cap.PhysicalEffectBudget(), None, {},
                    )
                )
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        self.assertEqual(aggregate["task_count"], 220)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 220)
        self.assertEqual(aggregate["canonical_projection_tasks"], 0)
        self.assertEqual(aggregate["canonical_column_handoff_tasks"], 0)
        self.assertEqual(aggregate["byte_exact_parent_handoff_tasks"], 0)
        self.assertEqual(aggregate["unsafe_handoff_tasks"], 0)

    @staticmethod
    def _synthetic_failure_row(task: dict[str, str]) -> dict:
        runner.configure()
        return runner._INHERITED_TERMINAL_OUTER_FAILURE(
            task, RuntimeError("x"), 1.0, cap.PhysicalEffectBudget(), None, {}
        )

    class _BudgetReplay:
        def __init__(self, value: dict) -> None:
            self.value = copy.deepcopy(value)

        def receipt(self) -> dict:
            return copy.deepcopy(self.value)

    class _CounterReplay:
        def __init__(self, value: dict) -> None:
            self.actual_logical_invocations = value["model_logical_requests"]
            self.requests = value["model_provider_requests"]
            self.attempts = value["model_provider_attempts"]
            self.calls = value["model_provider_successes"]
            self.acquisitions = value["model_slot_acquisitions"]
            self.failures = 0
            self.hard_total_wall_timeouts = 0

    class _SearchCounterReplay:
        def __init__(self, value: dict) -> None:
            self.actual_search_invocations = value["search_invocations"]
            self.actual_logical_query_count = value["logical_queries"]
            self.actual_fetch_invocations = value["fetch_invocations"]
            self.actual_fetch_request_count = value["fetch_requests"]
            self.fetch_calls = value["fetch_calls"]
            self.hard_fetch_helper_calls = value["fetch_helper_calls"]
            self.transport_failures = 0
            self.hard_total_wall_timeouts = 0
            self.fetch_helper_failures = 0
            self.hard_fetch_deadline_failures = 0
            self.fetch_deadline_rejections = 0

    class _CounterReplayFromAdmitted:
        def __init__(self, value: dict) -> None:
            count = value["model_admitted_count"]
            self.actual_logical_invocations = count
            self.requests = count
            self.attempts = count
            self.calls = count
            self.acquisitions = count
            self.failures = 0
            self.hard_total_wall_timeouts = 0

    class _SearchReplayFromAdmitted:
        def __init__(self, value: dict) -> None:
            self.actual_search_invocations = int(
                value["query_admitted_count"] > 0
            )
            self.actual_logical_query_count = value["query_admitted_count"]
            self.actual_fetch_invocations = int(
                value["fetch_admitted_count"] > 0
            )
            self.actual_fetch_request_count = value["fetch_admitted_count"]
            self.fetch_calls = value["fetch_admitted_count"]
            self.hard_fetch_helper_calls = self.actual_fetch_invocations
            self.transport_failures = 0
            self.hard_total_wall_timeouts = 0
            self.fetch_helper_failures = 0
            self.hard_fetch_deadline_failures = 0
            self.fetch_deadline_rejections = 0

    def test_visible_constraint_reach_is_exact95_of_220(self) -> None:
        limits = visible_schema.score.ScoreFirstLimits(**contract.LIMITS)
        counts = {name: 0 for name in (
            "active", "date_format", "numeric_scale", "explicit_order",
            "temporal_year_range", "rank_slots",
        )}
        for task in contract.task_vector(ROOT):
            plan, _observation, _source = visible_schema.projected_plan(
                {}, task["question"], limits
            )
            value = constraints.build_contract(task["question"], plan["columns"])
            counts["active"] += int(value["active_family_count"] > 0)
            for family in (
                "date_format", "numeric_scale", "explicit_order",
                "temporal_year_range", "rank_slots",
            ):
                counts[family] += int(value[family] is not None)
        self.assertEqual(counts, {
            "active": 95, "date_format": 46, "numeric_scale": 19,
            "explicit_order": 3, "temporal_year_range": 43, "rank_slots": 6,
        })

    def test_candidate_is_only_scored_prediction(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(
            policy[
                "scored_prediction_is_totality_constraint_candidate_or_safe_parent_handoff"
            ]
        )
        self.assertTrue(
            policy["constraint_contract_uses_only_visible_question_and_parent_table_columns"]
        )
        self.assertTrue(policy["control_retained_only_in_private_runtime_receipt"])
        self.assertTrue(policy["candidate_has_no_independent_model_or_sampling_effect"])
        self.assertFalse(policy["entropy_or_information_gain_assigns_signed_credit_or_routes"])

    def test_runner_rejects_privileged_input_before_wiring(self) -> None:
        task = dict(contract.task_vector(ROOT)[0])
        task["category"] = "forbidden"
        with mock.patch.object(runner.base, "run_one_task") as delegated:
            with self.assertRaises(ValueError):
                runner.run_one_task(task)
        delegated.assert_not_called()

    def test_runtime_ast_has_no_privileged_or_evaluator_capability(self) -> None:
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "split",
            "score",
            "reward",
        }
        hits: list[str] = []
        imports: list[str] = []
        for relative in (contract.CONTRACT, contract.RUNNER, contract.RUNTIME):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in privileged:
                        hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_contract_protocol_is_sealed_and_tamper_closed(self) -> None:
        with mock.patch.object(contract, "dependency_manifest", return_value={"x": "a" * 64}), mock.patch.object(
            contract, "parent_receipts", return_value={"parent": {"sha256": "b" * 64}}
        ), mock.patch.object(contract, "watcher_snapshot", return_value=[]), mock.patch.object(
            contract.task_parent, "_input_bindings", return_value={}
        ):
            protocol = contract.build_protocol(
                ROOT,
                now=1,
                tracked=False,
                require_pristine=False,
                build_audit_sha256="c" * 64,
            )
        self.assertTrue(contract.sealed(protocol, "protocol_payload_sha256"))
        self.assertEqual(
            protocol["execution"]["scored_prediction"],
            "constraint_candidate_safe_parent_handoff_or_canonical_column_handoff",
        )
        changed = copy.deepcopy(protocol)
        changed["execution"]["model_slot_cap"] = 15
        self.assertFalse(contract.sealed(changed, "protocol_payload_sha256"))

    def test_successor_surfaces_are_fresh(self) -> None:
        self.assertFalse((ROOT / contract.OUTPUT_ROOT).exists())
        for path in (
            contract.PREAUDIT,
            contract.EXECUTION_START,
            contract.ATTEMPT_CLAIM,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL,
            contract.RESULT,
            contract.POSTAUDIT,
        ):
            self.assertFalse((ROOT / path).exists())
        protocol_path = ROOT / contract.PROTOCOL
        if protocol_path.exists():
            protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
            self.assertEqual(
                contract.validate_protocol(ROOT, protocol), protocol
            )

    def test_finalizer_configures_fixed_evaluator_shell(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base.runner, runner)
        self.assertEqual(
            finalizer.base.base.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL
        )
        self.assertEqual(finalizer.base.base.EVALUATOR_WORKERS, 32)
        self.assertEqual(
            finalizer.base.base.REFERENCES["v25573_latest_complete"],
            contract.LATEST_RESULT,
        )
        self.assertIs(finalizer.base.base.contract, contract)
        self.assertEqual(finalizer.base.EVALUATOR_ROOT, finalizer.EVALUATOR_ROOT)
        self.assertIs(finalizer.base.base._forward_barrier, finalizer._forward_barrier)


if __name__ == "__main__":
    unittest.main()
