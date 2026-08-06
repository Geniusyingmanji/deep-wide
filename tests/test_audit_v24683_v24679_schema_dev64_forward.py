from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24683_v24679_schema_dev64_forward as audit  # noqa: E402


class V24683ForwardAuditTests(unittest.TestCase):
    def valid(self) -> dict:
        value = {
            "role": "v24683_v24679_schema_dev64_forward_audit",
            "protocol_id": audit.contract.PROTOCOL_ID,
            "audit_valid": True,
            "findings": [],
            "forward": {
                "selected_pair_tasks": 64,
                "real_child_runs": 72,
                "same_run_baseline_exact_reuse_tasks": 56,
                "changed_candidate_tasks": 7,
                "baseline_runtime_failures": 0,
                "candidate_runtime_failures": 0,
                "model_slot_timeouts": 0,
            },
            "reliability_gate": {"passed": True},
            "runtime_state": {
                "shared_api_lease_active": False,
                "forward_or_recovery_process_active": False,
                "recovery_tmux_session_absent": True,
            },
            "source_policy": {"official_evaluator_called": False},
            "claims": {"benchmark_score_available": False, "sota": False},
            "authorization": {
                "postfreeze_evaluator_gate_design": True,
                "evaluator_resource_open_or_execution": False,
                "additional_forward_resume_retry_or_rerun": False,
                "exact220": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        return value

    def test_valid_audit_authorizes_evaluator_gate_design_only(self) -> None:
        audit.validate_audit(self.valid())

    def test_resealed_changed_zero_fails_closed(self) -> None:
        value = copy.deepcopy(self.valid())
        value["forward"]["changed_candidate_tasks"] = 0
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(value)

    def test_resealed_runtime_failure_fails_closed(self) -> None:
        value = copy.deepcopy(self.valid())
        value["forward"]["candidate_runtime_failures"] = 1
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(value)

    def test_resealed_evaluator_authority_fails_closed(self) -> None:
        value = copy.deepcopy(self.valid())
        value["authorization"]["evaluator_resource_open_or_execution"] = True
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(value)

    def test_resealed_sota_claim_fails_closed(self) -> None:
        value = copy.deepcopy(self.valid())
        value["claims"]["sota"] = True
        value.pop("audit_payload_sha256")
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(value)


if __name__ == "__main__":
    unittest.main()
