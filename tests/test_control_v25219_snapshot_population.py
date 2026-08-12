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

from scripts import control_v25219_snapshot_population as target  # noqa: E402
from scripts import run_v25219_snapshot_population as runner  # noqa: E402


class V25219SnapshotPopulationControlTests(unittest.TestCase):
    def test_parent_controller_audit_is_exactly_bound(self) -> None:
        self.assertTrue(target._parent_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 47)

    def test_source_manifest_covers_runner_control_controller_transport_parser_selector(self) -> None:
        manifest = target._manifest()
        self.assertEqual(set(manifest), {str(path) for path in target.SOURCE_FILES})
        self.assertEqual(len(manifest), 9)

    def _preaudit(self):
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
                    "output_sha256": "f" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }
        audit = target.base.base
        with mock.patch.object(
            audit,
            "_git",
            side_effect=lambda *args: "same" if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")} else "",
        ), mock.patch.object(target, "_tests", return_value=fake_tests), mock.patch.object(
            audit,
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
        ), mock.patch.object(
            audit,
            "_watchers",
            return_value={
                str(pid): {
                    "present": True,
                    "start_ticks": ticks,
                    "matches_frozen_identity": True,
                }
                for pid, ticks in audit.PROTECTED_WATCHERS.items()
            },
        ), mock.patch.object(audit, "_lease_inactive", return_value=True), mock.patch.object(
            target, "_active_conflicts", return_value=[]
        ):
            return target.build_preactivation(now=1, tracked=False)

    def test_preactivation_authorizes_execution_start_generation_only(self) -> None:
        value = self._preaudit()
        self.assertEqual(
            runner.validate_preactivation_for_execution(
                value, expected_source_manifest=value["source_manifest"]
            ),
            value,
        )
        self.assertTrue(value["authorization"]["execution_start_generation"])
        self.assertFalse(value["authorization"]["single_public_snapshot_population_batch"])
        self.assertFalse(
            value["authorization"]["real_identity_selection_and_conditional_population_freeze"]
        )

    def test_execution_start_authorizes_exact_single_batch_only(self) -> None:
        preaudit = self._preaudit()
        audit = target.base.base
        with mock.patch.object(
            audit,
            "_git",
            side_effect=lambda *args: "a" * 40 if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")} else "",
        ):
            value = target.build_execution_start(preaudit, now=2, tracked=False)
        self.assertTrue(value["authorization"]["single_public_snapshot_population_batch"])
        self.assertTrue(
            value["authorization"]["real_identity_selection_and_conditional_population_freeze"]
        )
        self.assertFalse(value["authorization"]["retry_refetch_backfill_or_second_batch"])

    def test_resealed_preaudit_or_start_authority_tamper_fails(self) -> None:
        preaudit = self._preaudit()
        changed = copy.deepcopy(preaudit)
        changed["authorization"]["single_public_snapshot_population_batch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_preactivation(changed)
        hidden = copy.deepcopy(preaudit)
        hidden["hidden_runtime_authority"] = True
        hidden.pop("audit_payload_sha256")
        hidden["audit_payload_sha256"] = target.payload_sha256(hidden)
        with self.assertRaises(ValueError):
            target.validate_preactivation(hidden)
        hidden_watchers = copy.deepcopy(preaudit)
        hidden_watchers["runtime_state"]["protected_watchers"] = {}
        hidden_watchers.pop("audit_payload_sha256")
        hidden_watchers["audit_payload_sha256"] = target.payload_sha256(
            hidden_watchers
        )
        with self.assertRaises(ValueError):
            target.validate_preactivation(hidden_watchers)
        with self.assertRaises(ValueError):
            runner.validate_preactivation_for_execution(
                hidden_watchers,
                expected_source_manifest=hidden_watchers["source_manifest"],
            )
        audit = target.base.base
        with mock.patch.object(
            audit,
            "_git",
            side_effect=lambda *args: "a" * 40 if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")} else "",
        ):
            start = target.build_execution_start(preaudit, now=2, tracked=False)
        start["authorization"]["retry_refetch_backfill_or_second_batch"] = True
        start.pop("start_payload_sha256")
        start["start_payload_sha256"] = target.payload_sha256(start)
        with self.assertRaises(ValueError):
            target.validate_execution_start(start)
        hidden_start = copy.deepcopy(
            target.build_execution_start(preaudit, now=2, tracked=False)
        )
        hidden_start["hidden_runtime_authority"] = True
        hidden_start.pop("start_payload_sha256")
        hidden_start["start_payload_sha256"] = target.payload_sha256(hidden_start)
        with self.assertRaises(ValueError):
            target.validate_execution_start(hidden_start)


if __name__ == "__main__":
    unittest.main()
