from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25280_paired_checkpoint_reliability_external_contract as contract  # noqa: E402
from scripts import control_v25282_paired_checkpoint_reliability_launch as target  # noqa: E402
from scripts import run_v25280_paired_checkpoint_reliability_external as runner  # noqa: E402


class V25282PairedCheckpointReliabilityLaunchTests(unittest.TestCase):
    def test_runtime_manifest_build_audit_and_protocol_match_exactly(self) -> None:
        protocol = contract.validate_protocol(ROOT, target._read(contract.PROTOCOL))
        self.assertTrue(target._manifest_matches(protocol))
        build = target.build_control.validate_audit(target._read(contract.BUILD_AUDIT))
        self.assertTrue(build["audit_valid"])
        self.assertEqual(build["findings"], [])

    @staticmethod
    def _mocked_preaudit() -> dict:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
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
                for pattern, expected in target.TEST_SUITES
            ],
        }
        with mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(
            target.build_control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target.build_control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(
            target.build_control, "_active_conflicts", return_value=[]
        ):
            return target.build_preaudit(now=1, tracked=False)

    def test_preaudit_authorizes_start_generation_only(self) -> None:
        value = self._mocked_preaudit()
        self.assertEqual(target.validate_preaudit(value), value)
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["external_forward"])

    def test_resealed_preaudit_launch_credit_or_hidden_tamper_fails(self) -> None:
        value = self._mocked_preaudit()
        for kind in ("launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["external_forward"] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            else:
                changed["runtime_state"]["hidden_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_preaudit(changed)

    def test_preaudit_commit_boundary_requires_single_file_child(self) -> None:
        preaudit, head = {"git_head": "a" * 40}, "b" * 40

        def valid(*args: str) -> str:
            if args[0] == "rev-list":
                return f"{head} {'a' * 40}"
            if args[0] == "diff-tree":
                return str(contract.PREAUDIT)
            raise AssertionError(args)

        self.assertTrue(
            target.preaudit_commit_boundary(
                preaudit, preaudit_commit=head, git=valid
            )
        )
        for changed in (str(contract.PREAUDIT) + "\nplan.md", "plan.md"):
            def invalid(*args: str, changed: str = changed) -> str:
                if args[0] == "rev-list":
                    return f"{head} {'a' * 40}"
                if args[0] == "diff-tree":
                    return changed
                raise AssertionError(args)

            self.assertFalse(
                target.preaudit_commit_boundary(
                    preaudit, preaudit_commit=head, git=invalid
                )
            )

    def test_runner_execution_start_boundary_requires_single_file_and_push(self) -> None:
        start, head = {"git_head": "a" * 40}, "b" * 40

        def git(_root: Path, *args: str) -> str:
            if args[0] == "rev-list":
                return f"{head} {'a' * 40}"
            if args[0] == "diff-tree":
                return str(contract.EXECUTION_START)
            raise AssertionError(args)

        with mock.patch.object(contract, "git", side_effect=git):
            self.assertTrue(
                runner.execution_start_commit_boundary(
                    start, current_head=head, current_target=head
                )
            )
            self.assertFalse(
                runner.execution_start_commit_boundary(
                    start, current_head=head, current_target="c" * 40
                )
            )

    def test_start_schema_binds_estimand_caps_and_one_forward_only(self) -> None:
        protocol = contract.validate_protocol(ROOT, target._read(contract.PROTOCOL))
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25282_paired_checkpoint_reliability_execution_start",
                "protocol_id": contract.PROTOCOL_ID,
                "status": "authorized_not_started",
                "created_at_unix": 1,
                "git_head": "b" * 40,
                "protocol_sha256": target.PROTOCOL_SHA256,
                "preactivation_audit_sha256": "c" * 64,
                "source_manifest": protocol["source_manifest"],
                "task_vector_sha256": contract.TASK_VECTOR_SHA256,
                "selected": 20,
                "executor_concurrency": 20,
                "model_slot_cap": 16,
                "runtime_input_contract": ["opaque_id", "question"],
                "truthful_physical_caps": copy.deepcopy(contract.PHYSICAL_CAPS),
                "paired_estimand": {
                    "one_real_forward_per_task": True,
                    "candidate_local_same_checkpoint_projection": True,
                    "fixed_injected_stage": contract.runtime.INJECTED_STAGE,
                    "fixed_injected_failure_type": contract.runtime.INJECTED_FAILURE_TYPE,
                },
                "protected_watchers": contract.watcher_snapshot(),
                "findings": [],
                "authorization": {
                    "single_fresh20_paired_checkpoint_reliability_forward": True,
                    "retry_resume_skip_replacement_or_selective_rerun": False,
                    "candidate_quality_or_prediction_change_claim": False,
                    "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
                },
            },
            "execution_start_payload_sha256",
        )
        self.assertEqual(target.validate_start(value), value)
        changed = copy.deepcopy(value)
        changed["paired_estimand"]["fixed_injected_stage"] = "result_envelope_build"
        changed.pop("execution_start_payload_sha256")
        changed["execution_start_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_start(changed)

    def test_launch_manifest_change_fails_exact_match(self) -> None:
        value = {"launch_control_manifest": target._launch_manifest(tracked=False)}
        with mock.patch.object(
            target,
            "_launch_manifest",
            return_value=value["launch_control_manifest"],
        ):
            self.assertTrue(target._launch_manifest_matches(value))
            changed = copy.deepcopy(value)
            changed["launch_control_manifest"][str(target.SOURCE)] = "0" * 64
            self.assertFalse(target._launch_manifest_matches(changed))

    def test_launch_control_has_no_runtime_monkeypatch_or_evaluator_call(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("contract.runtime =", source)
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)


if __name__ == "__main__":
    unittest.main()
