from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audit_v24187_phase_liveness import (
    CAPACITY_STATE,
    EXECUTORS,
    ExecutorSpec,
    R1_STATE,
    actual_python_script,
    build_report,
    executor_report,
)


def _write(root: Path, relative: str, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _safe_fixture(root: Path) -> None:
    states = {
        R1_STATE: {
            "role": "v24118_r1_finalization_watchdog_state",
            "status": "waiting_for_r1_exact_terminal_220",
            "label_blind_before_exact220": True,
            "aggregate": {
                "selected": 220,
                "terminal": 129,
                "completed": 23,
                "failed": 106,
                "remaining": 91,
                "exact_terminal_220": False,
            },
            "mapping_or_gold_read": False,
            "evaluator_or_score_read": False,
            "benchmark_forward_api_called": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "leaderboard_submission_performed": False,
            "sota_claim": False,
        },
        CAPACITY_STATE: {
            "role": "v24164_scope_capacity_liveness_audit",
            "activation_ready": True,
            "wrapper": {"status": "waiting_for_p12_trial2_exact220_release"},
            "critical_findings": [],
            "degraded_findings": [],
            "source_policy": {
                "runtime_task_state_prediction_question_answer_or_evidence_opened": False
            },
            "claims": {"benchmark_score_available": False, "sota": False},
        },
        "outputs/v24155_avg4_after_scope_combined_watcher_state_v1_20260729.json": {
            "role": "v24155_avg4_after_scope_combined_watcher_state",
            "status": "waiting_for_combined_terminal_before_avg4",
            "leaderboard_submission_performed": False,
            "sota_claim": False,
        },
        "outputs/v2410_rank_slot_official_avg4_v8_watcher_state.json": {
            "role": "v2410_avg4_watcher_state",
            "status": "waiting_for_source_trial_2_exact220_release",
            "leaderboard_submission_performed": False,
            "sota_claim": False,
        },
        "outputs/v24107_paired_dev_liveness_watcher_state_v1_20260729.json": {
            "critical_findings": []
        },
        "outputs/v24176_predicate_completion_paired_dev_watcher_state_v1_20260730.json": {
            "role": "v24176_predicate_completion_paired_dev_watcher_state",
            "status": "waiting_for_official_avg4_terminal_serial_barrier",
            "test156_or_full220_launch_allowed": False,
            "test156_or_full220_api_called": False,
            "forward_resume_used": False,
            "selective_rerun_used": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "outputs/v24183_search_yield_launcher_state_v1_20260730.json": {
            "role": "v24183_search_yield_launcher_state",
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher": False,
            "network_model_search_fetch_or_benchmark_forward_called_by_launcher": False,
        },
        "outputs/v24180_predicate_search_yield_watcher_state_v1_20260730.json": {
            "role": "v24180_predicate_search_yield_watcher_state",
            "status": "waiting_for_schema77_paired_dev_terminal",
            "resume_or_selective_rerun_used": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "outputs/v24185_markdown_priority_launcher_state_v1_20260730.json": {
            "role": "v24185_markdown_priority_launcher_state",
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher": False,
            "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher": False,
        },
        "outputs/v24103_markdown_paired_dev_watcher_state_v1_20260728.json": {
            "role": "v24103_markdown_paired_dev_watcher_state",
            "status": "waiting_for_p12_four_trial_avg4_and_local_pack",
            "test156_or_full220_launch_allowed": False,
            "test156_or_full220_api_called": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "outputs/v24105_scope_open_paired_dev_watcher_state_v1_20260729.json": {
            "role": "v24105_scope_open_paired_dev_watcher_state",
            "status": "waiting_for_v24103_terminal_paired_go",
            "test156_or_full220_launch_allowed": False,
            "test156_or_full220_api_called": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "outputs/v24186_owic_after_quality_chain_launcher_state_v1_20260730.json": {
            "role": "v24186_owic_after_quality_chain_launcher_state",
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher": False,
            "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher": False,
        },
        "outputs/v2411_post_p12_owic_watcher_state_v8_20260727.json": {
            "role": "v2411_post_p12_owic_watcher_state",
            "status": "waiting_for_p12_trial2_exact220_release",
            "controller_enabled": False,
            "training_credit_enabled": False,
            "quality_leaderboard_or_sota_claim": False,
        },
        "outputs/v2410_p13_failure_taxonomy_v2_watcher_state.json": {
            "role": "v2410_p13_failure_taxonomy_v2_evidence_watcher_state",
            "status": "repeated_uncovered_evidence_requires_manual_audit",
            "terminal": 129,
            "mapped_failure_count": 100,
            "excluded_failure_count": 1,
            "uncovered_failure_count": 5,
            "new_p13_failure_mechanism_supported": False,
            "p13_design_allowed": False,
            "p13_implementation_allowed": False,
            "p13_forward_launch_allowed": False,
            "active_r1_or_frozen_p12_policy_change_allowed": False,
            "mapping_gold_category_evaluator_score_artifact_read": False,
            "runtime_prediction_values_used": False,
            "api_or_benchmark_forward_called": False,
            "leaderboard_or_sota_claim": False,
        },
        "outputs/v2410_leaderboard_postprocess_v4_watcher_state.json": {
            "role": "v2410_leaderboard_postprocess_watcher_state",
            "status": "waiting_for_four_exact220_trial_aggregate",
            "aggregate_present": False,
            "comparison_available": False,
            "leaderboard_submission_performed": False,
            "sota_claim": False,
            "mapping_gold_evaluator_task_prediction_or_current_task_score_read": False,
            "api_or_benchmark_forward_called": False,
        },
        "outputs/v24110_leaderboard_handoff_watcher_state_v1_20260728.json": {
            "role": "v24110_deepwide_leaderboard_handoff_watcher_state",
            "status": "waiting_for_four_exact220_avg4_pack_and_comparison_audit",
            "local_handoff_available": False,
            "leaderboard_submission_performed": False,
            "sota_claim": False,
        },
    }
    for relative, value in states.items():
        _write(root, relative, value)


def _rows() -> list[dict]:
    return [
        {
            "pid": index + 1,
            "argv": [
                "python",
                *( ["-I", "-B"] if spec.python_flags_required else ["-u"] ),
                spec.markers[0],
            ],
        }
        for index, spec in enumerate(EXECUTORS.values())
    ]


class AuditV24187PhaseLivenessTests(unittest.TestCase):
    def test_exact_executable_parser_ignores_option_marker(self) -> None:
        self.assertIsNone(
            actual_python_script(
                ["python", "-I", "-B", "-c", "x", "scripts/watch_fake.py"]
            )
        )
        self.assertEqual(
            actual_python_script(["python", "-I", "-B", "scripts/w.py"]),
            "scripts/w.py",
        )
        report = executor_report(
            [
                {
                    "pid": 1,
                    "argv": [
                        "python",
                        "-I",
                        "-B",
                        "other.py",
                        "--supersedes-watcher-marker",
                        "scripts/w.py",
                    ],
                }
            ],
            ExecutorSpec("x", ("scripts/w.py",)),
        )
        self.assertEqual(report["match_count"], 0)

    def test_r1_phase_is_healthy_with_manual_taxonomy_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _safe_fixture(root)
            with patch(
                "scripts.audit_v24187_phase_liveness._lease",
                return_value={
                    "present": False,
                    "active": False,
                    "ordinary": True,
                    "consistent": True,
                    "owner_registered": True,
                    "pid": None,
                    "contents_emitted": False,
                },
            ):
                value = build_report(root, now=100, processes=_rows())
        self.assertEqual(value["current_phase"]["phase"], "r1_full220")
        self.assertEqual(value["critical_findings"], [])
        self.assertEqual(
            value["overall_status"], "degraded_forward_healthy_manual_review_only"
        )
        self.assertIn(
            "taxonomy:repeated_uncovered_manual_review_only",
            value["degraded_findings"],
        )
        self.assertFalse(
            value["taxonomy"]["automatic_design_implementation_or_launch_allowed"]
        )

    def test_missing_current_executor_is_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _safe_fixture(root)
            rows = [
                row
                for row in _rows()
                if row["argv"][-1] != "scripts/watch_v24118_r1_finalization.py"
            ]
            with patch(
                "scripts.audit_v24187_phase_liveness._lease",
                return_value={
                    "present": False,
                    "active": False,
                    "ordinary": True,
                    "consistent": True,
                    "owner_registered": True,
                    "pid": None,
                    "contents_emitted": False,
                },
            ):
                value = build_report(root, now=100, processes=rows)
        self.assertIn(
            "current_phase:executor_process_identity", value["critical_findings"]
        )

    def test_auditor_source_has_no_mutation_network_or_forbidden_artifacts(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/audit_v24187_phase_liveness.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "ANTHROPIC_API_KEY",
            "TAVILY_API_KEY",
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
