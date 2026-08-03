from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    EVALUATOR_GATE,
    FINAL_RESULT,
    POSTAUDIT,
    PROTOCOL_ID,
    payload_sha256,
)
from scripts import finalize_v24330_shared_prefix_exact220 as target  # noqa: E402


def summary() -> dict:
    rows = []
    for index in range(220):
        split = "test" if index < 156 else "dev"
        rows.append(
            {
                "opaque_id": f"task_{index:024x}",
                "split": split,
                "runtime_status": "completed",
                "evaluator_valid": True,
                "metrics": {
                    "score": 1.0 if index == 0 else 0.0,
                    "entity_acc": 0.5,
                    "f1_by_row": 0.4,
                    "f1_by_item": 0.3,
                    "column_f1": 0.2,
                },
            }
        )
    return {
        "per_task": rows,
        "groups": {
            "test_156": {
                "selected": 156,
                "runtime_completed": 156,
                "runtime_failed": 0,
                "evaluator_valid": 156,
                "evaluator_invalid_or_not_run": 0,
                "process_trace_complete_tasks": 156,
                "conservative_all_selected": {
                    "score": 1 / 156,
                    "entity_acc": 0.5,
                    "f1_by_row": 0.4,
                    "f1_by_item": 0.3,
                    "column_f1": 0.2,
                },
                "cost_totals": {
                    "system_total_tokens": 1560.0,
                    "wall_seconds_sum": 312.0,
                },
            },
            "all_220": {
                "selected": 220,
                "runtime_completed": 220,
                "runtime_failed": 0,
                "evaluator_valid": 220,
                "evaluator_invalid_or_not_run": 0,
                "process_trace_complete_tasks": 220,
                "conservative_all_selected": {
                    "score": 1 / 220,
                    "entity_acc": 0.5,
                    "f1_by_row": 0.4,
                    "f1_by_item": 0.3,
                    "column_f1": 0.2,
                },
                "cost_totals": {
                    "system_total_tokens": 2200.0,
                    "wall_seconds_sum": 440.0,
                },
            },
        },
    }


def final_result_stub() -> dict:
    return {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_result",
        "protocol_id": PROTOCOL_ID,
        "status": "public_exact220_pair_no_go",
        "decision": {"status": "no_go"},
    }


class V24330FinalizerTests(unittest.TestCase):
    def test_test156_costs_use_group_totals_not_full220_summary(self) -> None:
        value = target._group_metrics(summary(), "test_156")
        self.assertEqual(value["selected"], 156)
        self.assertEqual(value["completed_tables"], 156)
        self.assertEqual(value["failed_tables"], 0)
        self.assertEqual(value["observable_system_total_tokens_lower_bound"], 1560)
        self.assertEqual(value["observable_task_wall_seconds_lower_bound"], 312.0)
        self.assertEqual(value["cost_trace_complete_tasks"], 156)
        all_value = target._group_metrics(summary(), "all_220")
        self.assertEqual(all_value["observable_system_total_tokens_lower_bound"], 2200)
        self.assertEqual(all_value["observable_task_wall_seconds_lower_bound"], 440.0)

    def test_process_detection_uses_actual_python_entrypoint(self) -> None:
        false_positive = [
            {
                "pid": 1,
                "argv": [
                    "bash",
                    "-lc",
                    "rg scripts/run_v24330_shared_prefix_exact220.py",
                ],
            }
        ]
        true_positive = [
            {
                "pid": 2,
                "argv": [
                    "/usr/bin/python3",
                    "-I",
                    "-B",
                    str(ROOT / target.RUNNER_MARKER),
                ],
            }
        ]
        with mock.patch.object(target, "process_snapshot", return_value=false_positive):
            self.assertFalse(target._process_present(target.RUNNER_MARKER))
        with mock.patch.object(target, "process_snapshot", return_value=true_positive):
            self.assertTrue(target._process_present(target.RUNNER_MARKER))

    def test_evaluator_start_requires_tracked_gate_and_clean_pushed_head(self) -> None:
        gate = {"passed": True}

        def git_output(_root: Path, *args: str) -> str:
            if args == ("status", "--porcelain"):
                return ""
            if args[:2] == ("ls-files", "--error-unmatch"):
                raise subprocess.CalledProcessError(1, args)
            return "a" * 40

        with mock.patch.object(target, "validate_protocol", return_value={}), mock.patch.object(
            target, "validate_evaluator_gate", return_value=gate
        ), mock.patch.object(target, "_git_output", side_effect=git_output), mock.patch.object(
            target, "lease_observation", return_value={"active": False}
        ), mock.patch.object(target, "sha256", return_value="b" * 64), mock.patch.object(
            target, "validate_evaluator_start", side_effect=lambda _root, value=None: value
        ):
            value = target.build_evaluator_start(ROOT, now=1)
        self.assertFalse(value["execution_authorized"])
        self.assertIn("evaluator_gate_not_tracked", value["findings"])

    def test_finalizer_validates_result_before_first_result_write(self) -> None:
        events: list[str] = []
        fake_result = final_result_stub()
        def git_output(_root: Path, *args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40

        with mock.patch.object(target, "validate_protocol", return_value={}), mock.patch.object(
            target, "validate_evaluator_start"
        ), mock.patch.object(target, "_git_output", side_effect=git_output), mock.patch.object(
            target, "_git_path_tracked", return_value=True
        ), mock.patch.object(target, "validate_forward_barrier", return_value={}), mock.patch.object(
            target, "validate_live_evaluator_identity", return_value={}
        ), mock.patch.object(target, "prepare_arm", return_value={"joined": []}), mock.patch.object(
            target, "acquire_deepwide_api_lease"
        ) as lease, mock.patch.object(
            target,
            "run_all_evaluators",
            return_value={"arms": {arm: {"rows": []} for arm in target.ARMS}},
        ), mock.patch.object(target, "summarize_rollout", return_value={}), mock.patch.object(
            target, "_new_json"
        ) as new_json, mock.patch.object(
            target, "build_final_result", return_value=fake_result
        ), mock.patch.object(
            target,
            "validate_final_result",
            side_effect=lambda *_args, **_kwargs: events.append("validate")
            or fake_result,
        ), mock.patch.object(
            target, "build_postaudit", return_value={"audit_valid": True}
        ), mock.patch.object(target, "read_object", return_value={"audit_valid": True}), mock.patch.object(
            target, "validate_postaudit"
        ):
            lease.return_value.__enter__.return_value = None
            target.finalize(ROOT)
        result_writes = [call for call in new_json.call_args_list if call.args[0] == ROOT / FINAL_RESULT]
        self.assertEqual(events, ["validate"])
        self.assertEqual(len(result_writes), 1)

    def test_audit_recovery_has_no_evaluator_or_prepare_call(self) -> None:
        for function in (target.recover_postaudit, target.seal_completed_evaluation):
            source = inspect.getsource(function)
            for forbidden in (
                "prepare_arm(",
                "run_all_evaluators(",
                "evaluator_command(",
                "acquire_deepwide_api_lease(",
            ):
                self.assertNotIn(forbidden, source)

    def test_recover_postaudit_only_writes_missing_audit(self) -> None:
        result = final_result_stub()
        audit = {
            "artifact_version": 1,
            "role": "v24330_shared_prefix_exact220_postresult_audit",
            "protocol_id": PROTOCOL_ID,
            "audit_valid": True,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            (root / FINAL_RESULT).parent.mkdir(parents=True, exist_ok=True)
            (root / FINAL_RESULT).write_text(json.dumps(result) + "\n", encoding="utf-8")
            writes: list[Path] = []

            def write(path: Path, value: dict) -> None:
                writes.append(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value) + "\n", encoding="utf-8")

            with mock.patch.object(target, "_process_present", return_value=False), mock.patch.object(
                target, "validate_protocol", return_value={}
            ), mock.patch.object(target, "validate_final_result", return_value=result), mock.patch.object(
                target, "build_postaudit", return_value=audit
            ), mock.patch.object(target, "_new_json", side_effect=write), mock.patch.object(
                target, "validate_postaudit", return_value=audit
            ):
                recovered = target.recover_postaudit(root)
            self.assertEqual(recovered, audit)
            self.assertEqual(writes, [root / POSTAUDIT])

    def test_final_result_validator_rejects_resealed_extra_field_first(self) -> None:
        value = final_result_stub()
        value["question"] = "forbidden"
        value["result_payload_sha256"] = payload_sha256(value)
        with mock.patch.object(target, "_recompute_final") as recompute:
            with self.assertRaisesRegex(RuntimeError, "final result drifted"):
                target.validate_final_result(ROOT, {}, value)
        recompute.assert_not_called()

    def test_gate_validator_rejects_resealed_extra_field(self) -> None:
        source = inspect.getsource(target.validate_evaluator_gate)
        self.assertIn("forward_result_tracked", source)
        self.assertIn("git_worktree_clean_before_gate", source)


if __name__ == "__main__":
    unittest.main()
