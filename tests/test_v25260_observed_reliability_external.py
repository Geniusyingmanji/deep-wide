from __future__ import annotations

import ast
import copy
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

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25260_observed_reliability_external as runner  # noqa: E402
from scripts import control_v25260_observed_reliability_external as control  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import CompatibleModel  # noqa: E402
from test_v25253_outer_physical_cap_observed_runtime import GroundedFrontierSearch  # noqa: E402


class V25260ObservedReliabilityExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tasks = contract.task_vector(ROOT)

    @staticmethod
    def _model(inner, root: Path):
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
        return DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )

    def _observed_fixture(self):
        target = contract.runtime
        parent = target.parent
        task = {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": (
                "Identify the country matching this public clue: "
                "<CLUE>capital New Delhi and currency INR</CLUE>. Resolve it from public "
                "pages, then use the visible IANA Root Zone Database authority. Return one "
                "table. Columns exactly: Domain | Type | TLD Manager. Preserve spelling."
            ),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            inner = CompatibleModel()
            budget = target.PhysicalEffectBudget()
            model = target.HardCappedModelLimiter(self._model(inner, root), budget)
            searches = {
                phase: target.HardCappedSearchClient(
                    GroundedFrontierSearch(task["question"], phase, field_page=False),
                    budget,
                    phase=phase,
                )
                for phase in parent.PHASES
            }
            result, stage = target.run_observed_task(
                task,
                model=model,
                searches=searches,
                limits=runner.ScoreFirstLimits(**contract.LIMITS),
                budget=budget,
                monotonic=time.monotonic,
            )
        return task, inner, budget, result, stage

    @staticmethod
    def _effect(budget) -> dict:
        receipt = budget.receipt()
        value = runner.transport._actual_effect_snapshot(None, {})
        value.update(
            model_logical_requests=receipt["model_admitted_count"],
            model_provider_requests=receipt["model_admitted_count"],
            model_provider_attempts=receipt["model_admitted_count"],
            model_provider_successes=receipt["model_admitted_count"],
            model_slot_acquisitions=receipt["model_admitted_count"],
            search_invocations=receipt["query_batch_attempt_count"],
            logical_queries=receipt["query_admitted_count"],
            fetch_invocations=receipt["fetch_batch_attempt_count"],
            fetch_requests=receipt["fetch_admitted_count"],
            fetch_calls=receipt["fetch_admitted_count"],
            fetch_helper_calls=receipt["fetch_batch_attempt_count"],
        )
        value.pop("snapshot_payload_sha256")
        value["snapshot_payload_sha256"] = runner.transport.contract.payload_sha256(value)
        return runner.transport._validate_actual_effect_snapshot(value)

    def test_frozen_population_is_exact64_by2_visible_only_and_hash_bound(self) -> None:
        entities = [
            package
            for task in self.tasks
            for package in contract.packages_from_question(task["question"])
        ]
        self.assertEqual(len(self.tasks), 64)
        self.assertEqual(len(entities), len(set(entities)), 128)
        self.assertEqual(contract.payload_sha256(self.tasks), contract.TASK_VECTOR_SHA256)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in self.tasks))

    def test_protocol_binds_truthful_caps_parent_limits_and_no_launch(self) -> None:
        value = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        self.assertEqual(contract.validate_protocol(ROOT, value), value)
        self.assertEqual(value["truthful_physical_caps"], {
            "queries_per_task": 4, "fetches_per_task": 14,
            "model_forwards_per_task": 4,
        })
        self.assertEqual(value["logical_parent_limits"]["fetch_targets"], 10)
        self.assertEqual(value["logical_parent_limits"]["model_calls"], 3)
        self.assertEqual(value["execution"]["executor_concurrency"], 32)
        self.assertFalse(value["authorization"]["external_forward"])

    def test_protocol_resealed_population_cap_launch_or_hidden_tamper_fails(self) -> None:
        value = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        for kind in ("population", "cap", "launch", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "population":
                changed["population"]["task_count"] = 63
            elif kind == "cap":
                changed["truthful_physical_caps"]["fetches_per_task"] = 15
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            else:
                changed["execution"]["hidden_router_label"] = "stratum"
            changed.pop("protocol_payload_sha256")
            changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                contract.validate_protocol(ROOT, changed)

    def test_attempt_claim_is_sealed_consumed_before_effect_and_label_blind(self) -> None:
        protocol = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        start = contract.seal(
            {"role": "v25262_observed_reliability_external_execution_start", "protocol_id": contract.PROTOCOL_ID},
            "execution_start_payload_sha256",
        )
        real = contract.sha256

        def hashes(path: Path) -> str:
            if Path(path).name in {contract.PROTOCOL.name, contract.EXECUTION_START.name}:
                return "b" * 64
            return real(path)

        with mock.patch.object(contract, "sha256", side_effect=hashes):
            value = runner.build_attempt_claim(protocol, start, now=1)
        self.assertEqual(runner.validate_attempt_claim(value), value)
        self.assertTrue(value["attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect"])
        self.assertFalse(value["mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"])

    def test_observed_success_row_preserves_prediction_and_effect_budget_parity(self) -> None:
        task, _inner, budget, result, stage = self._observed_fixture()
        row = runner._from_runtime(
            task, result, stage, 1.0, budget, None, {},
            health=runner.transport._health(), effect=self._effect(budget),
        )
        checked = runner.validate_task_row(row)
        self.assertTrue(checked["runtime_completed"])
        self.assertFalse(checked["failure_as_zero"])
        self.assertEqual(
            checked["prediction"], result["predictions"][contract.runtime.parent.CONTROL_ARM]
        )
        budget_receipt = checked["content_free_budget_receipt"]
        effect = checked["actual_effect_snapshot"]
        self.assertEqual(effect["logical_queries"], budget_receipt["query_admitted_count"])
        self.assertEqual(effect["fetch_requests"], budget_receipt["fetch_admitted_count"])
        self.assertEqual(effect["model_logical_requests"], budget_receipt["model_admitted_count"])
        self.assertLessEqual(effect["logical_queries"], 4)
        self.assertLessEqual(effect["fetch_requests"], 14)
        self.assertLessEqual(effect["model_logical_requests"], 4)

    def test_stage_failure_row_is_total_content_free_and_failure_as_zero(self) -> None:
        task = self.tasks[0]
        budget = contract.runtime.PhysicalEffectBudget()
        observer = contract.runtime.RuntimeStageObserver(budget)
        with self.assertRaises(contract.runtime.ObservedRuntimeStageError) as caught:
            observer.run("boundary", lambda: (_ for _ in ()).throw(ValueError("secret detail")))
        row = runner._terminal_outer_failure(
            task, caught.exception, 1.0, budget, None, {}
        )
        checked = runner.validate_task_row(row)
        encoded = json.dumps(checked, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("secret detail", encoded)
        self.assertTrue(checked["failure_as_zero"])
        self.assertEqual(checked["content_free_stage_receipt"]["failure_stage"], "boundary")
        self.assertEqual(checked["content_free_stage_receipt"]["failure_type"], "ValueError")

    def test_all_failure_fixed64_aggregate_is_valid_strict_no_go(self) -> None:
        rows = []
        for task in self.tasks:
            budget = contract.runtime.PhysicalEffectBudget()
            rows.append(runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0, budget, None, {}))
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.reliability_decision(aggregate)
        self.assertEqual(aggregate["terminal_tasks"], 64)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 64)
        self.assertFalse(decision["reliability_gate_passed"])
        self.assertIn("all_runtime_tasks_completed", decision["failed_checks"])

    def test_synthetic_total64_reliability_gate_go_requires_zero_failures(self) -> None:
        rows = []
        for task in self.tasks:
            budget = contract.runtime.PhysicalEffectBudget()
            row = runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0, budget, None, {})
            rows.append(row)
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        aggregate.update(
            completed_runtime_tasks=64,
            failure_as_zero_tasks=0,
            model_generated_tasks=64,
            fallback_tasks=0,
            stage_receipt_tasks=64,
        )
        self.assertTrue(runner.reliability_decision(runner.validate_aggregate(aggregate))["reliability_gate_passed"])

    def test_resealed_row_aggregate_credit_cap_or_hidden_tamper_fails(self) -> None:
        budget = contract.runtime.PhysicalEffectBudget()
        row = runner._terminal_outer_failure(self.tasks[0], RuntimeError("synthetic"), 1.0, budget, None, {})
        for kind in ("hidden", "credit", "cap"):
            changed = copy.deepcopy(row)
            if kind == "hidden":
                changed["content_free_budget_receipt"]["hidden"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["content_free_budget_receipt"]["fetch_cap"] = 15
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_source_is_label_blind_has_no_evaluator_import_and_fixed_concurrency(self) -> None:
        privileged = []
        evaluator_imports = []
        for relative in (contract.CONTRACT, contract.RUNNER):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=str(relative))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value in {
                        "category", "question_type", "task_category", "split",
                        "ground_truth", "gold", "answer_key", "score", "reward",
                    }
                ):
                    privileged.append((str(relative), node.lineno, node.slice.value))
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    evaluator_imports.extend(name for name in names if "evaluat" in name.casefold())
        self.assertEqual(privileged, [])
        self.assertEqual(evaluator_imports, [])
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 32)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.json"
            runner._publish_json(path, {"safe": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"safe": True})
            with self.assertRaises(FileExistsError):
                runner._publish_json(path, {"safe": True})

    def test_control_closure_and_build_authorization_are_exact(self) -> None:
        closure, vector = control._closure()
        self.assertEqual(len(closure), control.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(contract.payload_sha256(vector), control.EXPECTED_CLOSURE_VECTOR_SHA256)
        self.assertEqual(
            contract.payload_sha256([row["path"] for row in vector]),
            control.EXPECTED_CLOSURE_PATH_SHA256,
        )
        fake_tests = {
            "expected": control.EXPECTED_TESTS,
            "observed": control.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern, "expected": expected, "observed": expected,
                    "returncode": 0, "passed": True, "output_sha256": "c" * 64,
                }
                for pattern, expected in control.TEST_SUITES
            ],
        }
        with mock.patch.object(control, "_tests", return_value=fake_tests), mock.patch.object(
            control.audit,
            "_git",
            side_effect=lambda *args: "same" if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")} else "",
        ), mock.patch.object(control, "_endpoint_reachable", return_value=True), mock.patch.object(
            control, "_active_conflicts", return_value=[]
        ), mock.patch.object(control, "_lease_inactive", return_value=True), mock.patch.object(
            control, "_surfaces_pristine", return_value=True
        ):
            value = control.build_audit(now=1, tracked=False)
        self.assertEqual(control.validate_audit(value), value)
        self.assertTrue(value["authorization"]["protocol_generation"])
        self.assertFalse(value["authorization"]["external_forward"])
        for kind in ("launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_forward"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["runtime_state"]["hidden_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                control.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
