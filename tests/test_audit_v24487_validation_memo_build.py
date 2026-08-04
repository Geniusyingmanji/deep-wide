from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24487_validation_memo_build as target  # noqa: E402


class V24487ValidationMemoBuildAuditTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_validate_parents"),
            patch.object(
                target,
                "_run_test",
                return_value={
                    "passed": True,
                    "return_code": 0,
                    "elapsed_seconds": 5.0,
                },
            ),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: ""
                if args == ("status", "--porcelain")
                else "a" * 40,
            ),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            value = target.build_audit(now=0)
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        return value

    def test_clean_audit_authorizes_protocol_design_only(self) -> None:
        value = self.build_valid()
        self.assertEqual(value["tests"]["test_count"], 37)
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_equivalence_attack_and_fail_closed_evidence_is_bound(self) -> None:
        evidence = self.build_valid()["mechanism_evidence"]
        self.assertTrue(
            evidence[
                "slow_and_memoized_full_chain_outcome_and_artifacts_value_identical"
            ]
        )
        self.assertTrue(
            evidence[
                "cache_hits_recompute_outer_seal_and_compare_exact_bytes_and_type_shape"
            ]
        )
        self.assertEqual(evidence["explicit_frozen_binding_count"], 17)
        self.assertEqual(evidence["explicit_validator_layer_count"], 8)
        self.assertTrue(
            evidence[
                "invalid_memo_receipt_fails_before_success_terminal_and_worker_complete"
            ]
        )
        self.assertTrue(evidence["proof_certificate_and_exact_task_surface_unchanged"])

    def test_resealed_launch_rerun_or_evidence_tamper_fails(self) -> None:
        cases = (
            (
                "launch",
                lambda value: value["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
            (
                "rerun",
                lambda value: value["authorization"].__setitem__(
                    "same_v24484_population_rerun", True
                ),
            ),
            (
                "binding_count",
                lambda value: value["mechanism_evidence"].__setitem__(
                    "explicit_frozen_binding_count", 16
                ),
            ),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                value = copy.deepcopy(self.build_valid())
                alter(value)
                value.pop("audit_payload_sha256")
                value["audit_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(value)

    def test_slow_or_failed_worker_closes_authorization(self) -> None:
        for execution in (
            {"passed": False, "return_code": 1, "elapsed_seconds": 5.0},
            {"passed": True, "return_code": 0, "elapsed_seconds": 11.0},
        ):
            with self.subTest(execution=execution):
                def run_test(path, _timeout):
                    if path == target.WORKER_SUITE_PATH:
                        return execution
                    return {
                        "passed": True,
                        "return_code": 0,
                        "elapsed_seconds": 5.0,
                    }

                with (
                    patch.object(target, "_validate_parents"),
                    patch.object(target, "_run_test", side_effect=run_test),
                    patch.object(target.base, "_tracked", return_value=True),
                    patch.object(
                        target.base,
                        "_git",
                        side_effect=lambda *args: ""
                        if args == ("status", "--porcelain")
                        else "a" * 40,
                    ),
                    patch.object(
                        target,
                        "protected_watcher_snapshot",
                        return_value=target.EXPECTED_WATCHERS,
                    ),
                    patch.object(
                        target, "lease_observation", return_value={"active": False}
                    ),
                ):
                    value = target.build_audit(now=0)
                self.assertFalse(value["audit_valid"])
                self.assertFalse(
                    value["authorization"][
                        "fresh_disjoint_external_protocol_design"
                    ]
                )

    def test_runtime_sources_are_label_blind(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
