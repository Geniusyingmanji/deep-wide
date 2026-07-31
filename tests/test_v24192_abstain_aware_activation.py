from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.audit_v24192_abstain_aware_gate2a_activation import build_report
from scripts.preregister_v24160_true_continuation_liveness_schema import RUNNER_MARKER
from scripts.preregister_v24190_tie_aware_gate2a import (
    CONSUMER_MARKER as GRANDPARENT_CONSUMER_MARKER,
)
from scripts.preregister_v24191_policy_value_gate2a import (
    CONSUMER_MARKER as PARENT_CONSUMER_MARKER,
    STATE as PARENT_STATE,
)
from scripts.preregister_v24192_abstain_aware_gate2a import (
    CONSUMER_MARKER,
    PHASE_LIVENESS_MARKER,
    PHASE_LIVENESS_STATE,
    STATE,
)


def process(pid: int, marker: str) -> dict:
    return {"pid": pid, "argv": ["python", "-I", "-B", marker]}


class V24192AbstainAwareActivationTests(unittest.TestCase):
    @staticmethod
    def _files(root: Path, *, opened: bool = False) -> None:
        (root / "outputs").mkdir()
        phase = {
            "role": "v24187_phase_liveness_audit",
            "overall_status": "degraded_forward_healthy_manual_review_only",
            "critical_findings": [],
            "current_phase": {"phase": "r1_full220", "valid": True},
        }
        (root / PHASE_LIVENESS_STATE).write_text(json.dumps(phase), encoding="utf-8")
        parent = {
            "role": "v24191_policy_value_gate2a_consumer_state",
            "status": "waiting_for_v24190_tie_aware_gate2a_terminal",
            "parent_status": "waiting_for_true_continuation_audit_terminal",
            "parent_source_status": "waiting_for_p12_trial2_exact220_release",
            "parent_source_truth_fields_all_false": True,
            "parent_terminal": False,
            "parent_tie_aware_gate2a_evaluated": False,
            "terminal": False,
            "activation_ready": True,
            "manifest_model_prediction_or_outcome_opened": False,
            "policy_value_gate2a_evaluated": False,
            "controller_design_allowed": False,
            "training_credit_allowed": False,
            "full220_controller_launch_allowed": False,
        }
        (root / PARENT_STATE).write_text(json.dumps(parent), encoding="utf-8")
        state = {
            "role": "v24192_abstain_aware_gate2a_consumer_state",
            "protocol": {"sha256": "a" * 64},
            "status": "waiting_for_v24191_policy_value_gate2a_terminal",
            "parent_status": "waiting_for_v24190_tie_aware_gate2a_terminal",
            "ancestor_status": "waiting_for_true_continuation_audit_terminal",
            "ancestor_source_status": "waiting_for_p12_trial2_exact220_release",
            "ancestor_source_truth_fields_all_false": True,
            "parent_terminal": False,
            "parent_policy_value_gate2a_evaluated": False,
            "activation_ready": False,
            "manifest_model_prediction_or_outcome_opened": opened,
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer": False,
            "network_model_search_fetch_or_evaluator_api_called_by_consumer": False,
            "abstain_aware_gate2a_evaluated": False,
            "abstain_aware_gate2a_passed": False,
            "v24190_or_v24191_authoritative_for_controller_design": False,
            "controller_design_allowed": False,
            "controller_implementation_or_pilot_launch_allowed": False,
            "training_credit_allowed": False,
            "full220_controller_launch_allowed": False,
            "benchmark_or_sota_claim": False,
            "terminal": False,
        }
        (root / STATE).write_text(json.dumps(state), encoding="utf-8")

    def test_safe_wait_and_five_exact_processes_activate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._files(root)
            rows = [
                process(1, RUNNER_MARKER),
                process(2, PHASE_LIVENESS_MARKER),
                process(3, GRANDPARENT_CONSUMER_MARKER),
                process(4, PARENT_CONSUMER_MARKER),
                process(5, CONSUMER_MARKER),
            ]
            with mock.patch(
                "scripts.audit_v24192_abstain_aware_gate2a_activation.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ):
                report = build_report(root, created_at_unix=1, processes=rows)
            self.assertTrue(report["activation_valid"])
            self.assertTrue(
                report["boundary"]["v24190_grandparent_consumer_preserved"]
            )
            self.assertTrue(report["boundary"]["v24191_parent_consumer_preserved"])
            self.assertTrue(report["boundary"]["v24192_consumer_exactly_one"])

    def test_duplicate_successor_or_premature_open_fails_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._files(root, opened=True)
            rows = [
                process(1, RUNNER_MARKER),
                process(2, PHASE_LIVENESS_MARKER),
                process(3, GRANDPARENT_CONSUMER_MARKER),
                process(4, PARENT_CONSUMER_MARKER),
                process(5, CONSUMER_MARKER),
                process(6, CONSUMER_MARKER),
            ]
            with mock.patch(
                "scripts.audit_v24192_abstain_aware_gate2a_activation.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ):
                report = build_report(root, created_at_unix=1, processes=rows)
            self.assertFalse(report["activation_valid"])


if __name__ == "__main__":
    unittest.main()
