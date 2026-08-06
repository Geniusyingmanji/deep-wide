from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24681_v24679_zero_effect_start_failure as audit  # noqa: E402


class V24681ZeroEffectStartFailureTests(unittest.TestCase):
    def valid(self) -> dict:
        value = {
            "role": "v24681_v24679_zero_effect_start_failure",
            "protocol_id": audit.contract.PROTOCOL_ID,
            "audit_valid": True,
            "findings": [],
            "failure": {
                "missing_name": "FORWARD_AUDIT",
                "expected_error_observed": True,
                "missing_binding_precedes_lease_acquisition_in_frozen_source": True,
            },
            "effect_boundary": {
                "output_root_absent": True,
                "forward_result_absent": True,
                "forward_audit_absent": True,
                "shared_api_lease_acquired": False,
                "child_process_started": False,
                "child_terminal_receipt_created": False,
                "http_api_model_search_fetch_or_evaluator_effect": False,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            },
            "control": {"old_execution_start_reusable": False},
            "runtime_state": {
                "shared_api_lease_active": False,
                "v24679_process_active": False,
                "v24679_tmux_session_absent": True,
            },
            "authorization": {
                "reuse_v24679_execution_start": False,
                "restart_or_resume_v24679": False,
                "append_only_recovery_design": True,
                "forward_launch": False,
                "evaluator": False,
                "exact220": False,
            },
        }
        value["receipt_payload_sha256"] = audit.contract.payload_sha256(value)
        return value

    def test_valid_zero_effect_receipt(self) -> None:
        audit.validate_receipt(self.valid())

    def test_resealed_effect_tamper_fails_closed(self) -> None:
        value = self.valid()
        value["effect_boundary"]["child_process_started"] = True
        value.pop("receipt_payload_sha256")
        value["receipt_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_receipt(value)

    def test_resealed_old_start_reuse_fails_closed(self) -> None:
        value = copy.deepcopy(self.valid())
        value["control"]["old_execution_start_reusable"] = True
        value.pop("receipt_payload_sha256")
        value["receipt_payload_sha256"] = audit.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            audit.validate_receipt(value)

    def test_frozen_source_has_missing_binding_before_lease(self) -> None:
        source = (ROOT / audit.RUNNER).read_text(encoding="utf-8")
        self.assertTrue(audit._missing_binding_before_lease(source))


if __name__ == "__main__":
    unittest.main()
