from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as parser  # noqa: E402
from deepwide_agent import v25111_schema_recovered_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25115_schema_recovered_external_recovery_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelRequestError, ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from scripts import run_v25115_schema_recovered_external_recovery as runner  # noqa: E402
from scripts import control_v25115_schema_recovered_external_recovery as control  # noqa: E402
from test_v24990_query_vector_paired_runtime import SyntheticRobustSearch  # noqa: E402


class FourColumnModel:
    def __init__(self, *, fail_plan: bool = False, fail_proposal: bool = False) -> None:
        self.fail_plan = fail_plan
        self.fail_proposal = fail_proposal
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            if self.fail_plan:
                raise ModelRequestError("synthetic plan transport failure")
            text = json.dumps(
                {
                    "columns": ["wrong"],
                    "queries": ["one", "two", "three", "four"],
                }
            )
        elif self.logical_calls == 2:
            if self.fail_proposal:
                raise ModelRequestError("synthetic proposal transport failure")
            text = json.dumps(
                {
                    "records": [
                        {
                            "page_ordinal": 1,
                            "columns": [
                                {"column": column, "status": "unavailable"}
                                for column in contract.COLUMNS[1:]
                            ],
                        }
                    ]
                }
            )
        else:
            project = contract.PROJECTS[0]
            text = (
                "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
                "|---|---|---|---|\n"
                f"| {project} | Unknown | Unknown | Unknown |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class PackageAuthoritySearch(SyntheticRobustSearch):
    def __init__(self, question: str, project: str) -> None:
        super().__init__(question, "111")
        self.project = project

    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if output and output[0]["results"]:
            first = output[0]["results"][0]
            first["url"] = f"https://pypi.org/project/{self.project}"
            first["fetch_url"] = first["url"]
            first["title"] = f"{self.project} | PyPI"
        return output

    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        for batch in output:
            for result in batch["results"]:
                if "pypi.org/project/" in result["url"]:
                    content = (
                        f"{self.project} | PyPI\n"
                        "Latest version: 1.0.0\n"
                        "Latest release date: 2026-01-01\n"
                        "Requires-Python: >=3.10\n"
                    )
                    result["title"] = f"{self.project} | PyPI"
                    result["raw_content"] = content
                    result["content"] = ""
        return output


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(**contract.LIMITS)


class V25115SchemaRecoveredExternalRecoveryTests(unittest.TestCase):
    def _control_build(self) -> dict:
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        fake_semantic = {
            "dependency_closure": [],
            "dependency_closure_sha256": "0" * 64,
            "privileged_runtime_field_accesses": [],
            "allowed_provider_rank_access": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
        }
        fake_freshness = {
            "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
            "project_count": 20,
            "all_literal_zero_hit": True,
            "rows": [],
            "network_endpoint_page_value_model_or_evaluator_access": False,
        }
        frozen_watchers = [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ]
        with mock.patch.object(control, "_tests", return_value=fake_tests), mock.patch.object(
            control, "_semantic_audit", return_value=fake_semantic
        ), mock.patch.object(
            control, "_history_freshness", return_value=fake_freshness
        ), mock.patch.object(control, "_parent_valid", return_value=True), mock.patch.object(
            control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            control, "_future_pristine", return_value=True
        ), mock.patch.object(contract, "watcher_snapshot", return_value=frozen_watchers):
            return control.build_audit(now=1, require_clean=False)

    def _runtime_row(
        self,
        index: int = 0,
        *,
        fail_plan: bool = False,
        fail_proposal: bool = False,
    ) -> dict:
        task = contract.task_vector()[index]
        project = contract.PROJECTS[index]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for slot in range(1, contract.MODEL_SLOT_CAP + 1):
                (slots / f"slot_{slot:02d}.lock").write_text("{}\n", encoding="utf-8")
            inner = FourColumnModel(
                fail_plan=fail_plan,
                fail_proposal=fail_proposal,
            )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=root,
                slot_cap=contract.MODEL_SLOT_CAP,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: PackageAuthoritySearch(task["question"], project)
                for phase in runtime.PHASES
            }
            result = runtime.run_paired_task(
                task,
                model=model,
                searches=searches,
                limits=limits(),
                arm_order=contract.arm_order_vector()[index],
            )
            self.assertEqual(inner.logical_calls, 4)
            return runner._from_runtime(
                task,
                contract.arm_order_vector()[index],
                result,
                runner._health(),
            )

    def test_fresh_population_exact_schema_and_reduced_slot_cap(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(set(contract.PROJECTS)), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 4)
        self.assertEqual(
            sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()),
            10,
        )
        self.assertTrue(
            all(
                parser.extract_exact_visible_columns(task["question"])
                == list(contract.COLUMNS)
                for task in tasks
            )
        )

    def test_source_policy_and_failure_gate_are_explicit(self) -> None:
        policy = contract.source_policy()
        gate = contract.mechanism_gate()
        self.assertTrue(policy["columns_exactly_pipe_schema_parsed_from_visible_question_only"])
        self.assertTrue(
            policy[
                "plan_proposal_transport_and_representation_failures_accounted_separately"
            ]
        )
        self.assertTrue(
            policy["model_slot_cap_reduced_from_eight_to_four_with_twenty_task_concurrency"]
        )
        for name in (
            "maximum_plan_model_effect_failures",
            "maximum_plan_transport_failures",
            "maximum_plan_output_validation_failures",
            "maximum_proposal_model_effect_failures",
            "maximum_proposal_transport_failures",
            "maximum_representation_validation_failures",
        ):
            self.assertEqual(gate[name], 0)

    def test_real_successor_row_binds_runtime_and_stage_seals(self) -> None:
        row = runner.validate_task_row(self._runtime_row())
        stage = row["stage_failure_accounting"]
        receipt = row["content_free_receipt"]
        self.assertTrue(row["runtime_completed"])
        self.assertEqual(stage["visible_schema_column_count"], 4)
        self.assertFalse(stage["plan_model_effect_failed"])
        self.assertFalse(stage["proposal_model_effect_failed"])
        self.assertFalse(stage["representation_validation_failed"])
        self.assertEqual(receipt["physical_model_logical_call_count"], 4)
        self.assertEqual(receipt["physical_query_count"], 4)
        self.assertTrue(all(row["model_success"].values()))

    def test_plan_and_proposal_transport_are_separate_from_representation(self) -> None:
        row = runner.validate_task_row(
            self._runtime_row(fail_plan=True, fail_proposal=True)
        )
        stage = row["stage_failure_accounting"]
        self.assertTrue(stage["plan_model_effect_failed"])
        self.assertTrue(stage["plan_transport_failed"])
        self.assertTrue(stage["proposal_model_effect_failed"])
        self.assertTrue(stage["proposal_transport_failed"])
        self.assertFalse(stage["representation_validation_failed"])
        self.assertEqual(stage["visible_schema_column_count"], 4)
        self.assertTrue(all(row["model_success"].values()))

    def test_stage_failure_aggregate_cannot_pass(self) -> None:
        good = self._runtime_row()
        failed = self._runtime_row(fail_plan=True, fail_proposal=True)
        rows: list[dict] = []
        for index in range(contract.TASK_COUNT):
            source = failed if index == 0 else good
            changed = copy.deepcopy(source)
            changed["opaque_id"] = contract.task_vector()[index]["opaque_id"]
            changed["arm_order"] = contract.arm_order_vector()[index]
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            rows.append(changed)
        # This test targets aggregation only; the separately tested row validator
        # binds each real row to its opaque runtime payload.
        original = runner.validate_task_row
        try:
            runner.validate_task_row = lambda value: dict(value)
            aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        finally:
            runner.validate_task_row = original
        self.assertEqual(aggregate["plan_transport_failure_tasks"], 1)
        self.assertEqual(aggregate["proposal_transport_failure_tasks"], 1)
        self.assertEqual(aggregate["representation_validation_failure_tasks"], 0)
        self.assertFalse(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])

    def test_ideal_aggregate_requires_all_mechanism_thresholds(self) -> None:
        aggregate = {
            "task_count": 20,
            "terminal_tasks": 20,
            "completed_runtime_tasks": 20,
            "failure_as_zero_tasks": 0,
            "both_arms_model_success_tasks": 20,
            "tasks_with_usable_page": 16,
            "verifier_exposure_tasks": 8,
            "prediction_changed_tasks": 4,
            "exposed_and_prediction_changed_tasks": 4,
            "unexposed_and_prediction_changed_tasks": 0,
            "plan_model_effect_failure_tasks": 0,
            "plan_transport_failure_tasks": 0,
            "plan_output_validation_failure_tasks": 0,
            "proposal_model_effect_failure_tasks": 0,
            "proposal_transport_failure_tasks": 0,
            "representation_validation_failure_tasks": 0,
            "post_synthesis_accounting_or_receipt_validation_failure_tasks": 0,
            "planned_queries": 80,
            "physical_queries": 80,
            "physical_fetches": 200,
            "physical_model_logical_calls": 80,
            "control_effective_model_logical_calls": 60,
            "candidate_effective_model_logical_calls": 60,
            "control_evidence_characters": 1_000,
            "candidate_evidence_characters": 1_000,
            "outer_hard_failures": 0,
            "terminal_transport_timeout_helper_or_model_hard_failures": 0,
            "control_arm_model_hard_failures": 0,
            "candidate_arm_model_hard_failures": 0,
        }
        self.assertTrue(runner.mechanism_decision(aggregate)["mechanism_gate_passed"])
        for name in (
            "plan_transport_failure_tasks",
            "proposal_transport_failure_tasks",
            "representation_validation_failure_tasks",
        ):
            changed = copy.deepcopy(aggregate)
            changed[name] = 1
            with self.subTest(name=name):
                self.assertFalse(
                    runner.mechanism_decision(changed)["mechanism_gate_passed"]
                )

    def test_resealed_stage_runtime_or_privileged_tamper_fails(self) -> None:
        row = self._runtime_row()
        for kind in ("stage", "runtime", "privileged"):
            changed = copy.deepcopy(row)
            if kind == "stage":
                changed["stage_failure_accounting"]["plan_transport_failed"] = True
            elif kind == "runtime":
                changed["runtime_result_payload_sha256"] = "0" * 64
            else:
                changed["category"] = "forbidden"
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises((RuntimeError, ValueError)):
                runner.validate_task_row(changed)

    def test_failure_as_zero_is_terminal_and_cannot_pass(self) -> None:
        failure = runner._terminal_outer_failure(
            contract.task_vector()[0],
            contract.arm_order_vector()[0],
            ValueError("x"),
            1.0,
            runner._health(),
        )
        checked = runner.validate_task_row(failure)
        self.assertTrue(checked["failure_as_zero"])
        self.assertFalse(checked["runtime_completed"])

    def test_forward_sources_are_label_blind_and_evaluator_absent(self) -> None:
        forbidden = {
            "category",
            "question_type",
            "ground_truth",
            "answer_key",
            "gold",
            "score",
            "reward",
        }
        accesses: list[str] = []
        for relative in (
            contract.RUNNER,
            Path("src/deepwide_agent/v25111_schema_recovered_paired_runtime.py"),
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    if node.slice.value in forbidden:
                        accesses.append(str(node.slice.value))
        self.assertEqual(accesses, [])
        self.assertFalse((ROOT / contract.EVALUATOR).exists())

    def test_build_audit_authorizes_protocol_only(self) -> None:
        value = control.validate_build(self._control_build())
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["protocol_generation_after_build_commit_push"])
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_protocol_freezes_population_and_twenty_by_four_scheduling(self) -> None:
        value = contract.build_protocol(
            ROOT,
            now=1,
            tracked=False,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )
        self.assertEqual(value["population"]["task_count"], 20)
        self.assertEqual(value["execution"]["executor_concurrency"], 20)
        self.assertEqual(value["execution"]["model_slot_cap"], 4)
        self.assertTrue(value["execution"]["exact_visible_schema_recovery"])
        self.assertEqual(
            value["recovery_parent"]["failed_protocol_sha256"],
            contract.FAILED_PARENT_PROTOCOL_SHA256,
        )
        self.assertEqual(value["recovery_parent"]["failed_parent_runtime_effects"], 0)
        self.assertFalse(
            value["authorization"]["failed_v25113_protocol_activation_or_resume"]
        )
        self.assertFalse(value["authorization"]["deepwidebench_dev64_exact220_or_sota"])

    def test_resealed_build_launch_authority_tamper_fails(self) -> None:
        changed = copy.deepcopy(self._control_build())
        changed["authorization"]["external_forward"] = True
        changed.pop("audit_payload_sha256")
        changed = contract.seal(changed, "audit_payload_sha256")
        with self.assertRaises(RuntimeError):
            control.validate_build(changed)


if __name__ == "__main__":
    unittest.main()
