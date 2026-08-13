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

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from scripts import control_v25310_worldbank_monotone_fill_launch as target  # noqa: E402
from scripts import run_v25309_worldbank_monotone_fill_external as runner  # noqa: E402


def _tests() -> dict:
    suites = [
        {
            "pattern": pattern,
            "expected": expected,
            "observed": expected,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }
        for pattern, expected in target.TEST_SUITES
    ]
    return {
        "expected": target.EXPECTED_TESTS,
        "observed": target.EXPECTED_TESTS,
        "passed": True,
        "suites": suites,
    }


class V25310WorldBankMonotoneFillLaunchTests(unittest.TestCase):
    def test_frozen_build_and_protocol_hashes_validate(self) -> None:
        self.assertEqual(
            contract.sha256(ROOT / contract.BUILD_AUDIT), target.BUILD_AUDIT_SHA256
        )
        self.assertEqual(
            contract.sha256(ROOT / contract.PROTOCOL), target.PROTOCOL_SHA256
        )
        protocol = contract.validate_protocol(ROOT, target._read(contract.PROTOCOL))
        self.assertFalse(protocol["authorization"]["external_forward"])

    def test_build_preaudit_roundtrip_without_effect(self) -> None:
        with mock.patch.object(target, "_tests", return_value=_tests()), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(
            target.build_control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target.build_control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.runner, "_active_conflicts", return_value=[]):
            value = target.build_preaudit(now=1, tracked=False)
        self.assertEqual(target.validate_preaudit(value), value)
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["external_forward"])

    def test_preaudit_tamper_fails(self) -> None:
        with mock.patch.object(target, "_tests", return_value=_tests()), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(
            target.build_control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target.build_control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.runner, "_active_conflicts", return_value=[]):
            value = target.build_preaudit(now=1, tracked=False)
        changed = copy.deepcopy(value)
        changed["authorization"]["postfreeze_evaluator"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_preaudit(changed)

    def test_start_roundtrip_is_forward_only(self) -> None:
        with mock.patch.object(target, "_tests", return_value=_tests()), mock.patch.object(
            target, "_future_pristine", return_value=True
        ), mock.patch.object(
            target.build_control, "_lease_inactive", return_value=True
        ), mock.patch.object(
            target.build_control, "_endpoint_reachable", return_value=True
        ), mock.patch.object(target.runner, "_active_conflicts", return_value=[]):
            preaudit = target.build_preaudit(now=1, tracked=False)
        real_read = target._read

        def read(relative: Path):
            if relative == contract.PREAUDIT:
                return preaudit
            return real_read(relative)

        real_sha = contract.sha256

        def digest(path: Path):
            if Path(path) == ROOT / contract.PREAUDIT:
                return "c" * 64
            return real_sha(path)

        with mock.patch.object(target, "_read", side_effect=read), mock.patch.object(
            contract, "sha256", side_effect=digest
        ):
            start = target.build_start(now=2, tracked=False)
        self.assertEqual(target.validate_start(start), start)
        self.assertTrue(
            start["authorization"]["single_fresh12_worldbank_monotone_fill_forward"]
        )
        self.assertFalse(start["authorization"]["postfreeze_evaluator"])

    def test_preaudit_and_execution_start_commit_boundaries(self) -> None:
        preaudit = {"git_head": "a" * 40}

        def git(*args: str) -> str:
            if args[:4] == ("rev-list", "--parents", "-n", "1"):
                return f"{'b' * 40} {'a' * 40}"
            if args[:4] == ("diff-tree", "--no-commit-id", "--name-only", "-r"):
                return str(contract.PREAUDIT)
            raise AssertionError(args)

        self.assertTrue(
            target.preaudit_commit_boundary(
                preaudit, preaudit_commit="b" * 40, git=git
            )
        )
        start = {"git_head": "c" * 40}

        def runner_git(_root: Path, *args: str) -> str:
            if args[:4] == ("rev-list", "--parents", "-n", "1"):
                return f"{'d' * 40} {'c' * 40}"
            if args[:4] == ("diff-tree", "--no-commit-id", "--name-only", "-r"):
                return str(contract.EXECUTION_START)
            raise AssertionError(args)

        with mock.patch.object(contract, "git", side_effect=runner_git):
            self.assertTrue(
                runner.execution_start_commit_boundary(
                    start, current_head="d" * 40, current_target="d" * 40
                )
            )

    def test_start_tamper_changes_evaluator_authority_and_fails(self) -> None:
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25310_worldbank_monotone_fill_execution_start",
                "protocol_id": contract.PROTOCOL_ID,
                "status": "authorized_not_started",
                "created_at_unix": 1,
                "git_head": "b" * 40,
                "protocol_sha256": target.PROTOCOL_SHA256,
                "preactivation_audit_sha256": "c" * 64,
                "source_manifest": {},
                "task_vector_sha256": contract.TASK_VECTOR_SHA256,
                "page_vector_sha256": contract.RENDERED_PAGES_SHA256,
                "selected": 12,
                "executor_concurrency": 20,
                "model_slot_cap": 8,
                "runtime_input_contract": ["opaque_id", "question"],
                "physical_caps": contract.PHYSICAL_CAPS,
                "mechanism_gate": contract.mechanism_gate(),
                "protected_watchers": contract.watcher_snapshot(),
                "findings": [],
                "authorization": {
                    "single_fresh12_worldbank_monotone_fill_forward": True,
                    "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
                    "postfreeze_evaluator": True,
                    "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
                },
            },
            "execution_start_payload_sha256",
        )
        with self.assertRaises(ValueError):
            target.validate_start(value)


if __name__ == "__main__":
    unittest.main()
