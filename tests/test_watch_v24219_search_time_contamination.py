from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24219_search_time_contamination import payload_sha256
from scripts import watch_v24219_search_time_contamination as watch


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
        "role": "v24218_exact220_executor_watcher_state",
        "status": status,
        "terminal": terminal,
        "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["state_payload_sha256"] = payload_sha256(value)
    return value


class WatchV24219SearchTimeContaminationTests(unittest.TestCase):
    def test_preterminal_reads_only_parent_envelope(self) -> None:
        with tempfile.TemporaryDirectory(dir=watch.ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent_state",
                return_value=(
                    parent(terminal=False, status="waiting"),
                    "waiting",
                ),
            ), mock.patch.object(watch, "validate_terminal_authority") as authority, mock.patch.object(
                watch, "publish_audit"
            ) as publisher:
                value = watch.run_cycle(watch.ROOT, state_path=state, now=1)
        authority.assert_not_called()
        publisher.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24218_exact220_terminal")
        self.assertFalse(value["task_manifest_or_evidence_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_terminal_parent_without_result_stops(self) -> None:
        with tempfile.TemporaryDirectory(dir=watch.ROOT / "outputs") as directory:
            state = Path(directory) / "state.json"
            with mock.patch.object(watch, "validate_protocol", return_value=VERIFIED), mock.patch.object(
                watch, "_activation", return_value=ACTIVATION
            ), mock.patch.object(
                watch,
                "_parent_state",
                return_value=(
                    parent(terminal=True, status="terminal_fail_closed_no_retry"),
                    "terminal_without_result",
                ),
            ):
                value = watch.run_cycle(watch.ROOT, state_path=state, now=1)
        self.assertTrue(value["terminal"])
        self.assertFalse(value["audit_started"])

    def test_complete_parent_runs_exactly_one_offline_audit(self) -> None:
        authority = {
            "result": {"path": "result", "sha256": "r" * 64},
            "forward_barrier": {"path": "barrier", "sha256": "b" * 64},
            "runtime_completed": 100,
            "runtime_failed": 120,
        }
        report_value = {
            "role": "v24219_search_time_contamination_public_aggregate",
            "parent": authority,
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
                        status="complete_exact220_local_result_released_not_sota",
                    ),
                    "complete",
                ),
            ), mock.patch.object(
                watch, "validate_terminal_authority", return_value=authority
            ), mock.patch.object(watch, "file_sha256", return_value="x" * 64):
                value = watch.run_cycle(
                    watch.ROOT, state_path=state, now=1, publisher=publisher
                )
        self.assertTrue(value["terminal"])
        self.assertEqual(value["tasks_scanned"], 220)
        self.assertIsNone(value["confirmed_eal"])


if __name__ == "__main__":
    unittest.main()
