from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24219_search_time_contamination import payload_sha256
from scripts import audit_v24219_search_time_contamination_wait as audit


PROTOCOL = {"sha256": "p" * 64}
ACTIVATION = {"sha256": "a" * 64}


def wait_state() -> dict:
    value = {
        "role": "v24219_search_time_contamination_watcher_state",
        "protocol": {"sha256": "p" * 64},
        "execution_activation": {"sha256": "a" * 64},
        "parent_safe_state_envelope_opened": True,
        "parent_terminal_result_and_barrier_validated": False,
        "task_manifest_or_evidence_opened": False,
        "audit_started": False,
        "report_created": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "forward_result_evaluator_or_watcher_modified": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
        "parent_state": {"terminal": False},
        "status": "waiting_for_v24218_exact220_terminal",
        "reason": "parent_preterminal",
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class AuditV24219SearchTimeContaminationWaitTests(unittest.TestCase):
    def test_wait_audit_proves_no_task_content_or_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / audit.STATE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(wait_state()), encoding="utf-8")
            with mock.patch.object(audit, "validate_protocol", return_value=PROTOCOL), mock.patch.object(
                audit, "validate_activation", return_value=ACTIVATION
            ), mock.patch.object(audit, "_present", return_value=False), mock.patch.object(
                audit, "file_sha256", return_value="s" * 64
            ):
                value = audit.build_audit(root, created_at_unix=1)
        self.assertFalse(value["boundary"]["task_manifest_or_evidence_opened"])
        self.assertFalse(
            value["boundary"]["network_model_search_fetch_evaluator_or_api_called"]
        )

    def test_wait_audit_rejects_early_audit(self) -> None:
        state = wait_state()
        state["audit_started"] = True
        unsigned = dict(state)
        unsigned.pop("state_payload_sha256")
        state["state_payload_sha256"] = payload_sha256(unsigned)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / audit.STATE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state), encoding="utf-8")
            with mock.patch.object(audit, "validate_protocol", return_value=PROTOCOL), mock.patch.object(
                audit, "validate_activation", return_value=ACTIVATION
            ), mock.patch.object(audit, "_present", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "wait boundary"):
                    audit.build_audit(root, created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
