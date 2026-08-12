from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25232_header_totality_shadow_runtime as shadow_runtime  # noqa: E402
from deepwide_agent import v25244_header_totality_shadow_external_contract as contract  # noqa: E402
from scripts import run_v25244_header_totality_shadow_external as runner  # noqa: E402
from scripts import control_v25244_header_totality_shadow_external as control  # noqa: E402
import test_v25232_header_totality_shadow_runtime as shadow_fixture  # noqa: E402


class V25244HeaderTotalityShadowExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tasks = contract.task_vector(ROOT)

    def test_frozen_population_authority_and_task_hashes_are_exact(self) -> None:
        self.assertEqual(len(self.tasks), 64)
        self.assertEqual(contract.payload_sha256(self.tasks), contract.TASK_VECTOR_SHA256)
        self.assertEqual(
            contract.payload_sha256([row["opaque_id"] for row in self.tasks]),
            contract.OPAQUE_ID_VECTOR_SHA256,
        )
        self.assertEqual(
            contract.payload_sha256([row["question"] for row in self.tasks]),
            contract.QUESTION_VECTOR_SHA256,
        )
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in self.tasks))

    def test_protocol_binds_production_model_search_budget_and_concurrency(self) -> None:
        value = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        self.assertEqual(contract.validate_protocol(ROOT, value), value)
        self.assertEqual(value["model"]["name"], "gpt-5.6-sol")
        self.assertEqual(value["execution"]["executor_concurrency"], 32)
        self.assertEqual(value["execution"]["model_slot_cap"], 16)
        self.assertEqual(value["limits"]["search_queries"], 4)
        self.assertEqual(value["limits"]["fetch_targets"], 10)
        self.assertEqual(value["limits"]["model_calls"], 3)
        self.assertFalse(value["authorization"]["external_forward"])

    def test_protocol_resealed_population_budget_launch_or_hidden_tamper_fails(self) -> None:
        value = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        for kind in ("population", "budget", "launch", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "population":
                changed["population"]["task_count"] = 63
            elif kind == "budget":
                changed["limits"]["fetch_targets"] = 11
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            else:
                changed["execution"]["hidden_router_label"] = "stratum"
            changed.pop("protocol_payload_sha256")
            changed["protocol_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                contract.validate_protocol(ROOT, changed)

    def test_attempt_claim_is_sealed_and_consumed_before_effect(self) -> None:
        protocol = contract.build_protocol(source_manifest={"safe.py": "a" * 64}, now=1)
        start = contract.seal(
            {
                "role": "v25244_header_totality_shadow_external_execution_start",
                "protocol_id": contract.PROTOCOL_ID,
            },
            "execution_start_payload_sha256",
        )
        real = contract.sha256

        def hashes(path: Path) -> str:
            value = Path(path)
            if value.name in {contract.PROTOCOL.name, contract.EXECUTION_START.name}:
                return "b" * 64
            return real(value)

        with mock.patch.object(contract, "sha256", side_effect=hashes):
            claim = runner.build_attempt_claim(protocol, start, now=1)
        self.assertEqual(runner.validate_attempt_claim(claim), claim)
        self.assertTrue(
            claim["attempt_authority_consumed_before_endpoint_model_search_fetch_or_output_effect"]
        )
        changed = copy.deepcopy(claim)
        changed["retry_resume_skip_replacement_selective_rerun_or_second_attempt"] = True
        changed.pop("claim_payload_sha256")
        changed["claim_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            runner.validate_attempt_claim(changed)

    def test_real_safe_shadow_success_row_preserves_parent_exactly(self) -> None:
        fixture = shadow_fixture.V25232HeaderTotalityShadowRuntimeTests()
        _inner, result = fixture._run(shadow_runtime, shadow_fixture.SAFE_SHADOW)
        sparse = result
        for _ in range(5):
            sparse = sparse["parent_result"]
        receipt = sparse["content_free_receipt"]
        effect = runner._actual_effect_snapshot(None, {})
        effect.update(
            model_logical_requests=receipt["provider_forward_count"],
            model_provider_requests=receipt["model_provider_request_count"],
            model_provider_attempts=receipt["model_provider_attempt_count"],
            logical_queries=receipt["physical_query_count"],
            fetch_requests=receipt["physical_fetch_count"],
            fetch_calls=receipt["physical_fetch_count"],
        )
        effect.pop("snapshot_payload_sha256")
        effect["snapshot_payload_sha256"] = contract.payload_sha256(effect)
        row = runner._from_runtime(
            shadow_fixture.TASK, result, 1.0, effect=effect
        )
        checked = runner.validate_task_row(row)
        receipt = checked["content_free_shadow_receipt"]
        self.assertEqual(receipt["shadow_entry_count"], 1)
        self.assertEqual(receipt["shadow_completed_count"], 1)
        self.assertEqual(receipt["shadow_candidate_available_count"], 1)
        self.assertFalse(checked["parent_behavior_drift"])
        self.assertFalse(checked["shadow_prediction_changed"])
        self.assertEqual(checked["predictions"], result["parent_result"]["predictions"])
        self.assertEqual(checked["prediction_sha256"], result["parent_result"]["prediction_sha256"])

    def test_outer_failure_row_is_total_content_bounded_and_fail_closed(self) -> None:
        row = runner._terminal_outer_failure(self.tasks[0], RuntimeError("secret detail"), 1.0)
        self.assertEqual(runner.validate_task_row(row), row)
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("secret detail", encoded)
        self.assertTrue(row["failure_as_zero"])
        self.assertFalse(row["runtime_completed"])
        self.assertIsNone(row["content_free_shadow_receipt"])
        self.assertEqual(row["predictions"][contract.CONTROL_ARM], row["predictions"][contract.CANDIDATE_ARM])

    def test_all_failure_fixed64_aggregate_is_valid_strict_no_go(self) -> None:
        rows = [
            runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0)
            for task in self.tasks
        ]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["task_count"], 64)
        self.assertEqual(aggregate["terminal_tasks"], 64)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 64)
        self.assertFalse(decision["mechanism_gate_passed"])
        self.assertIn("natural_shadow_entry_nonzero", decision["failed_checks"])
        self.assertIn("safe_shadow_candidate_nonzero", decision["failed_checks"])

    def test_one_safe_shadow_with_all_64_completed_satisfies_only_preregistered_gate(self) -> None:
        failures = [
            runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0)
            for task in self.tasks
        ]
        aggregate = runner.aggregate_rows(failures, wall_seconds=2.0)
        aggregate.update(
            completed_runtime_tasks=64,
            failure_as_zero_tasks=0,
            shadow_eligibility_tasks=1,
            shadow_entry_tasks=1,
            shadow_completed_tasks=1,
            safe_shadow_candidate_tasks=1,
            content_free_shadow_receipt_valid_tasks=64,
        )
        checked = runner.validate_aggregate(aggregate)
        decision = runner.mechanism_decision(checked)
        self.assertTrue(decision["mechanism_gate_passed"])
        self.assertTrue(decision["independent_activation_and_quality_design"])
        self.assertFalse(decision["candidate_activation_or_prediction_change"])
        self.assertFalse(decision["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"])

    def test_aggregate_and_forward_resealed_safety_or_credit_tamper_fails(self) -> None:
        rows = [
            runner._terminal_outer_failure(task, RuntimeError("synthetic"), 1.0)
            for task in self.tasks
        ]
        aggregate = runner.aggregate_rows(rows, wall_seconds=2.0)
        for kind in ("drift", "credit"):
            changed = copy.deepcopy(aggregate)
            if kind == "drift":
                changed["parent_behavior_drift_tasks"] = 1
            else:
                changed["positive_signed_credit_count"] = 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_aggregate(changed)

    def test_source_is_label_blind_has_no_evaluator_and_fixed_executor_slots(self) -> None:
        files = (ROOT / contract.CONTRACT, ROOT / contract.RUNNER)
        privileged = []
        evaluator_imports = []
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value in {
                        "category", "question_type", "task_category", "split",
                        "ground_truth", "gold", "answer_key", "score", "reward",
                    }
                ):
                    privileged.append((path.name, node.lineno, node.slice.value))
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = (
                        [alias.name for alias in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
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
        self.assertEqual(len(closure), 76)
        self.assertEqual(
            contract.payload_sha256(vector), control.EXPECTED_CLOSURE_VECTOR_SHA256
        )
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
                    "pattern": pattern,
                    "expected": expected,
                    "observed": expected,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "c" * 64,
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
