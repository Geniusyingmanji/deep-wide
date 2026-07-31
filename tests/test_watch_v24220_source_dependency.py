from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24220_source_dependency import payload_sha256
from scripts import watch_v24220_source_dependency as watch


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}
ACTIVATION = {
    "path": str(watch.ACTIVATION),
    "sha256": "a" * 64,
    "watcher_pid": 7,
    "watcher_start_ticks": 9,
}


def parent(*, terminal: bool, status: str) -> dict:
    value = {
        "role": "v24219_search_time_contamination_watcher_state",
        "status": status,
        "terminal": terminal,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class WatchV24220SourceDependencyTests(unittest.TestCase):
    def test_preterminal_reads_only_parent_envelope(self) -> None:
        with tempfile.TemporaryDirectory(dir=watch.ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent_state",
                return_value=(parent(terminal=False, status="waiting"), "waiting"),
            ), mock.patch.object(
                watch, "validate_parent_terminal_authority"
            ) as authority, mock.patch.object(watch, "publish_audit") as publisher:
                value = watch.run_cycle(watch.ROOT, state_path=state, now=1)
        authority.assert_not_called()
        publisher.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24219_contamination_terminal")
        self.assertFalse(value["task_evidence_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_terminal_parent_without_report_stops(self) -> None:
        with tempfile.TemporaryDirectory(dir=watch.ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent_state",
                return_value=(
                    parent(terminal=True, status="terminal_fail_closed"),
                    "terminal_without_result",
                ),
            ):
                value = watch.run_cycle(watch.ROOT, state_path=state, now=1)
        self.assertTrue(value["terminal"])
        self.assertFalse(value["audit_started"])

    def test_complete_parent_runs_exactly_one_offline_audit(self) -> None:
        report_value = {
            "role": "v24220_source_dependency_public_aggregate",
            "official_primary_denominator": 220,
            "leaderboard_submission_or_sota_claim": False,
            "aggregate": {"tasks_scanned": 220},
        }
        with tempfile.TemporaryDirectory(dir=watch.ROOT / "outputs") as directory:
            base = Path(directory)
            state = base / "state.json"
            report = base / "report.json"

            def publisher(_root):
                report.write_text("{}", encoding="utf-8")
                return report_value

            with mock.patch.object(watch, "REPORT", report), mock.patch.object(
                watch, "validate_protocol", return_value=VERIFIED
            ), mock.patch.object(watch, "_activation", return_value=ACTIVATION), mock.patch.object(
                watch,
                "_parent_state",
                return_value=(
                    parent(
                        terminal=True,
                        status="complete_post_terminal_contamination_audit",
                    ),
                    "complete",
                ),
            ), mock.patch.object(
                watch, "validate_parent_terminal_authority", return_value={}
            ), mock.patch.object(watch, "file_sha256", return_value="x" * 64):
                value = watch.run_cycle(
                    watch.ROOT, state_path=state, now=1, publisher=publisher
                )
        self.assertTrue(value["terminal"])
        self.assertEqual(value["tasks_scanned"], 220)
        self.assertTrue(value["official_primary_result_unchanged"])


if __name__ == "__main__":
    unittest.main()
