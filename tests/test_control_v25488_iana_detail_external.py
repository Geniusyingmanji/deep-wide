from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import control_v25488_iana_detail_external as target  # noqa: E402


class V25488ControlTests(unittest.TestCase):
    def test_parent_barriers_are_exact_and_test_denominator_is_frozen(self) -> None:
        self.assertTrue(target._parent_barriers())
        self.assertTrue(target._clone_namespace_ready())
        self.assertEqual(target.EXPECTED_TESTS, 61)

    def test_build_audit_authorizes_protocol_generation_only(self) -> None:
        tests = {
            "expected": 61,
            "observed": 61,
            "passed": True,
            "suites": [],
        }
        semantic = {
            "dependency_closure": [],
            "dependency_closure_sha256": "a" * 64,
            "privileged_runtime_field_accesses": [],
            "evaluator_capabilities": [],
            "credential_literal_hits": [],
            "allowed_provider_rank_access": [target.ALLOWED_PROVIDER_SCORE_ACCESS],
        }
        watchers = [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in target.contract.EXPECTED_WATCHERS
        ]
        with (
            mock.patch.object(target, "_clean_pushed", return_value=("a", "a")),
            mock.patch.object(
                target.contract, "dependency_manifest", return_value={"x": "y"}
            ),
            mock.patch.object(target, "_tests", return_value=tests),
            mock.patch.object(target, "_semantic_audit", return_value=semantic),
            mock.patch.object(target, "_parent_barriers", return_value=True),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(
                target.contract, "watcher_snapshot", return_value=watchers
            ),
            mock.patch.object(target, "_lease_inactive", return_value=True),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build(value), value)
        self.assertTrue(
            value["authorization"]["protocol_generation_after_build_commit_push"]
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_resealed_parent_credit_or_launch_tamper_fails(self) -> None:
        expected = {
            "execution_start_generation": True,
            "external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        value = target.contract.seal(
            {
                "artifact_version": 1,
                "role": "v25488_iana_detail_external_preactivation_audit",
                "protocol_id": target.contract.PROTOCOL_ID,
                "audit_valid": True,
                "findings": [],
                "checks": {"x": True},
                "tests": {"observed": 61},
                "authorization": expected,
            },
            "audit_payload_sha256",
        )
        self.assertEqual(target.validate_preaudit(value), value)
        changed = copy.deepcopy(value)
        changed["authorization"]["external_forward"] = True
        changed.pop("audit_payload_sha256")
        changed = target.contract.seal(changed, "audit_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate_preaudit(changed)

    def test_future_surfaces_include_quality_and_are_append_only(self) -> None:
        surfaces = target.contract.future_surfaces()
        self.assertIn(target.contract.POSTFREEZE_QUALITY_PROTOCOL, surfaces)
        self.assertIn(target.contract.QUALITY_RESULT, surfaces)
        self.assertIn(target.contract.QUALITY_AUDIT, surfaces)
        self.assertIn(target.contract.OUTPUT_ROOT, surfaces)


if __name__ == "__main__":
    unittest.main()
