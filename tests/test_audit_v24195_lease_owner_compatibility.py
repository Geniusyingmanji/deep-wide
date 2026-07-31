from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.audit_v24195_lease_owner_compatibility import (
    EXPECTED_PARENT_FINDING,
    REGISTERED_OWNER,
    REGISTERED_PURPOSE,
    build_report,
    validate_successor_identity,
)


def parent(*_args, **_kwargs):
    critical = list(_kwargs.pop("critical", []))
    return {
        "role": "v24187_phase_liveness_audit",
        "overall_status": (
            "critical_manual_audit_required_no_automatic_mutation"
            if critical
            else "healthy"
        ),
        "critical_findings": critical,
        "degraded_findings": [],
        "audit_payload_sha256": "a" * 64,
    }


class AuditV24195LeaseOwnerCompatibilityTests(unittest.TestCase):
    def _build(self, lease: dict, parent_findings: list[str], identity=None):
        verified = {
            "path": Path("protocol.json"),
            "sha256": "c" * 64,
            "value": {
                "decision_contract_sha256": "d" * 64,
                "control_surface": {"manifest_sha256": "e" * 64},
            },
        }

        def builder(*_args, **_kwargs):
            return parent(critical=parent_findings)

        patches = [
            mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.validate_protocol",
                return_value=verified,
            )
        ]
        if identity is not None:
            patches.append(
                mock.patch(
                    "scripts.audit_v24195_lease_owner_compatibility.validate_successor_identity",
                    return_value=identity,
                )
            )
        with patches[0]:
            if len(patches) == 2:
                with patches[1]:
                    return build_report(
                        Path("/tmp").resolve(),
                        now=1,
                        processes=[],
                        parent_builder=builder,
                        observed_lease=lease,
                    )
            return build_report(
                Path("/tmp").resolve(),
                now=1,
                processes=[],
                parent_builder=builder,
                observed_lease=lease,
            )

    def test_inactive_lease_preserves_parent_exactly(self) -> None:
        lease = {
            "present": False,
            "active": False,
            "ordinary": True,
            "record_valid": True,
            "owner": None,
            "purpose": None,
            "pid": None,
            "lock_holder_pids": [],
        }
        report = self._build(lease, ["unrelated"])
        self.assertEqual(report["critical_findings"], ["unrelated"])
        self.assertEqual(report["compatibility"]["suppressed_expected_parent_findings"], [])

    def test_exact_registered_identity_suppresses_only_expected_finding(self) -> None:
        lease = {
            "present": True,
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "owner": REGISTERED_OWNER,
            "purpose": REGISTERED_PURPOSE,
            "pid": 7,
            "lock_holder_pids": [7],
        }
        identity = {
            "valid": True,
            "findings": [],
            "successor_protocol_sha256": "f" * 64,
            "successor_activation_sha256": "1" * 64,
            "executor_pid": 7,
            "executor_start_ticks": 99,
        }
        report = self._build(
            lease, [EXPECTED_PARENT_FINDING, "unrelated"], identity
        )
        self.assertEqual(report["critical_findings"], ["unrelated"])
        self.assertEqual(
            report["compatibility"]["suppressed_expected_parent_findings"],
            [EXPECTED_PARENT_FINDING],
        )
        self.assertTrue(
            report["compatibility"]["unrelated_parent_critical_findings_preserved"]
        )

    def test_wrong_owner_or_purpose_fails_closed(self) -> None:
        base = {
            "present": True,
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "pid": 7,
            "lock_holder_pids": [7],
        }
        wrong_owner = self._build(
            {**base, "owner": "unknown", "purpose": REGISTERED_PURPOSE},
            [EXPECTED_PARENT_FINDING],
        )
        self.assertIn("v24195:unknown_lease_owner", wrong_owner["critical_findings"])
        invalid_identity = {
            "valid": False,
            "findings": ["lease_purpose"],
            "successor_protocol_sha256": None,
            "successor_activation_sha256": None,
            "executor_pid": 7,
            "executor_start_ticks": 99,
        }
        wrong_purpose = self._build(
            {**base, "owner": REGISTERED_OWNER, "purpose": "wrong"},
            [EXPECTED_PARENT_FINDING],
            invalid_identity,
        )
        self.assertIn(
            "v24195:registered_successor_identity_invalid",
            wrong_purpose["critical_findings"],
        )
        self.assertIn(EXPECTED_PARENT_FINDING, wrong_purpose["critical_findings"])

    def test_pid_reuse_and_forged_activation_fail_identity(self) -> None:
        lease = {
            "present": True,
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "owner": REGISTERED_OWNER,
            "purpose": REGISTERED_PURPOSE,
            "pid": 101,
            "lock_holder_pids": [101],
        }
        protocol = {
            "path": Path("p"),
            "sha256": "p" * 64,
            "value": {},
        }
        activation = {
            "role": "v24196_capacity_executor_activation",
            "activation_valid": True,
            "protocol": {"path": "results/v24196_capacity_executor_preregistration_v1_20260731.json", "sha256": "p" * 64},
            "compatibility": {"path": "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json", "sha256": "c" * 64},
            "registered_shared_lease_owner": REGISTERED_OWNER,
            "registered_shared_lease_purpose": REGISTERED_PURPOSE,
            "executor": {"marker": "scripts/watch_v24196_capacity_executor.py", "pid": 101, "start_ticks": 500},
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
            "activation_payload_sha256": "forged",
        }
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            (proc / "101").mkdir()
            fields = ["S"] + ["0"] * 18 + ["999"] + ["0"] * 8
            (proc / "101/stat").write_text(
                "101 (python) " + " ".join(fields), encoding="utf-8"
            )
            with mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility._successor_protocol",
                return_value=protocol,
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.ordinary",
                return_value=Path(directory) / "activation.json",
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.read_object",
                return_value=activation,
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.sha256",
                return_value="a" * 64,
            ):
                result = validate_successor_identity(
                    Path(directory),
                    compatibility_sha="c" * 64,
                    lease=lease,
                    proc_root=proc,
                    processes=[
                        {
                            "pid": 101,
                            "argv": [
                                "python",
                                "-I",
                                "-B",
                                "scripts/watch_v24196_capacity_executor.py",
                            ],
                        }
                    ],
                )
        self.assertFalse(result["valid"])
        self.assertIn("successor_activation_contract", result["findings"])
        self.assertIn("successor_executor_start_ticks", result["findings"])

    def test_successor_without_isolated_no_bytecode_flags_fails_identity(self) -> None:
        lease = {
            "present": True,
            "active": True,
            "ordinary": True,
            "record_valid": True,
            "owner": REGISTERED_OWNER,
            "purpose": REGISTERED_PURPOSE,
            "pid": 101,
            "lock_holder_pids": [101],
        }
        activation = {
            "role": "v24196_capacity_executor_activation",
            "activation_valid": True,
            "protocol": {"path": "results/v24196_capacity_executor_preregistration_v1_20260731.json", "sha256": "p" * 64},
            "compatibility": {"path": "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json", "sha256": "c" * 64},
            "registered_shared_lease_owner": REGISTERED_OWNER,
            "registered_shared_lease_purpose": REGISTERED_PURPOSE,
            "executor": {"marker": "scripts/watch_v24196_capacity_executor.py", "pid": 101, "start_ticks": 500},
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "network_model_search_fetch_or_evaluator_api_called": False,
        }
        from scripts.preregister_v24195_lease_owner_compatibility import payload_sha

        activation["activation_payload_sha256"] = payload_sha(activation)
        protocol = {"path": Path("p"), "sha256": "p" * 64, "value": {}}
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            (proc / "101").mkdir()
            fields = ["S"] + ["0"] * 18 + ["500"] + ["0"] * 8
            (proc / "101/stat").write_text(
                "101 (python) " + " ".join(fields), encoding="utf-8"
            )
            with mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility._successor_protocol",
                return_value=protocol,
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.ordinary",
                return_value=Path(directory) / "activation.json",
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.read_object",
                return_value=activation,
            ), mock.patch(
                "scripts.audit_v24195_lease_owner_compatibility.sha256",
                return_value="a" * 64,
            ):
                result = validate_successor_identity(
                    Path(directory),
                    compatibility_sha="c" * 64,
                    lease=lease,
                    proc_root=proc,
                    processes=[
                        {
                            "pid": 101,
                            "argv": [
                                "python",
                                "scripts/watch_v24196_capacity_executor.py",
                            ],
                        }
                    ],
                )
        self.assertFalse(result["valid"])
        self.assertIn("successor_executor_python_flags", result["findings"])

    def test_source_has_no_network_mutation_or_benchmark_artifact_surface(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/audit_v24195_lease_owner_compatibility.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "os.kill",
            "signal.",
            "requests.",
            "urllib",
            "socket.",
            "runtime_predictions.jsonl",
            "evaluator_mapping.jsonl",
            "--resume",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
