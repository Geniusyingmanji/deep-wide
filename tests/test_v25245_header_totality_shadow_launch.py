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

from deepwide_agent import v25244_header_totality_shadow_external_contract as contract  # noqa: E402
from scripts import control_v25245_header_totality_shadow_launch as target  # noqa: E402


class V25245HeaderTotalityShadowLaunchTests(unittest.TestCase):
    def test_manifest_matches_frozen_protocol_exactly(self) -> None:
        protocol = contract.validate_protocol(ROOT, target._read(contract.PROTOCOL))
        self.assertTrue(target._manifest_matches(protocol))

    @staticmethod
    def _mocked_preaudit() -> dict:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        with mock.patch.object(target, "_tests", return_value=fake_tests), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(target.build_control, "_lease_inactive", return_value=True), mock.patch.object(
            target.build_control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.build_control, "_active_conflicts", return_value=[]):
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
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["runtime_state"]["hidden_authority"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_preaudit(changed)

    def test_preaudit_commit_boundary_requires_single_file_child(self) -> None:
        preaudit = {"git_head": "a" * 40}
        head = "b" * 40

        def valid(*args: str) -> str:
            if args[0] == "rev-list":
                return f"{head} {'a' * 40}"
            if args[0] == "diff-tree":
                return str(contract.PREAUDIT)
            raise AssertionError(args)

        self.assertTrue(target.preaudit_commit_boundary(preaudit, preaudit_commit=head, git=valid))
        for kind in ("extra_file", "extra_parent"):
            def invalid(*args: str) -> str:
                if args[0] == "rev-list":
                    suffix = f" {'c' * 40}" if kind == "extra_parent" else ""
                    return f"{head} {'a' * 40}{suffix}"
                if args[0] == "diff-tree":
                    return str(contract.PREAUDIT) + ("\nplan.md" if kind == "extra_file" else "")
                raise AssertionError(args)
            with self.subTest(kind=kind):
                self.assertFalse(target.preaudit_commit_boundary(preaudit, preaudit_commit=head, git=invalid))

    def test_execution_start_commit_boundary_requires_single_file_and_push(self) -> None:
        start = {"git_head": "a" * 40}
        head = "b" * 40

        def valid(*args: str) -> str:
            if args[0] == "rev-list":
                return f"{head} {'a' * 40}"
            if args[0] == "diff-tree":
                return str(contract.EXECUTION_START)
            raise AssertionError(args)

        self.assertTrue(target.execution_start_commit_boundary(start, current_head=head, current_target=head, git=valid))
        self.assertFalse(target.execution_start_commit_boundary(start, current_head=head, current_target="c" * 40, git=valid))

    def test_start_schema_authorizes_one_shadow_forward_only(self) -> None:
        protocol = contract.validate_protocol(ROOT, target._read(contract.PROTOCOL))
        value = {
            "artifact_version": 1,
            "role": "v25244_header_totality_shadow_external_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "status": "authorized_not_started",
            "created_at_unix": 1,
            "git_head": "b" * 40,
            "protocol_sha256": target.PROTOCOL_SHA256,
            "preactivation_audit_sha256": "c" * 64,
            "source_manifest": protocol["source_manifest"],
            "task_vector_sha256": contract.TASK_VECTOR_SHA256,
            "selected": 64,
            "executor_concurrency": 32,
            "model_slot_cap": 16,
            "runtime_input_contract": ["opaque_id", "question"],
            "protected_watchers": contract.watcher_snapshot(),
            "findings": [],
            "authorization": {
                "single_fresh64_shadow_forward": True,
                "retry_resume_skip_replacement_or_selective_rerun": False,
                "candidate_activation_or_prediction_change": False,
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            },
        }
        value = contract.seal(value, "execution_start_payload_sha256")
        self.assertEqual(target.validate_start(value), value)

    def test_launch_control_has_no_runtime_monkeypatch_or_evaluator_import(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("contract.runtime =", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("official_eval", source)


if __name__ == "__main__":
    unittest.main()
