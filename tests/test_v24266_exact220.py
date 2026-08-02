from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    build_v24259_fallback_result,
)
from scripts import activate_v24266_exact220 as activation_target  # noqa: E402
from scripts import audit_v24266_exact220 as audit_target  # noqa: E402
from scripts import finalize_v24266_exact220 as finalizer  # noqa: E402
from scripts import run_v24266_exact220 as runner  # noqa: E402
from scripts.preregister_v24266_exact220 import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    MODEL_SLOT_CAP,
    SELECTED_COUNT,
    build_protocol,
    selected_ids,
    selected_shards,
)
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return a table. Column names: Name, Value.",
    }


def fallback(position: int, limits: ScoreFirstLimits) -> dict:
    return build_v24259_fallback_result(
        visible(position),
        limits=limits,
        completion_kind="worker_failure_fallback",
        failure_stage="test_executor",
        failure_type="SyntheticFailure",
        elapsed_seconds=0.1,
    )


class V24266Exact220Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = build_protocol(ROOT, now=1, require_pristine=False)
        cls.limits = ScoreFirstLimits(**dict(cls.protocol["limits"]))

    def test_partition_is_exact_disjoint_52_52_52_64(self) -> None:
        shards = selected_shards(ROOT)
        self.assertEqual([(tag, len(ids)) for tag, ids in shards], [("test_s01", 52), ("test_s02", 52), ("test_s03", 52), ("devval", 64)])
        ids = selected_ids(ROOT)
        self.assertEqual(len(ids), SELECTED_COUNT)
        self.assertEqual(len(set(ids)), SELECTED_COUNT)

    def test_protocol_freezes_candidate_four_by_two_and_no_extra_rollout(self) -> None:
        value = self.protocol
        self.assertEqual(value["candidate"]["policy_id"], "v24259_deterministic_table_normalizer_v1")
        self.assertEqual(value["task_contract"]["selected_count"], SELECTED_COUNT)
        self.assertEqual(value["forward_contract"]["executor_concurrency"], 4)
        self.assertEqual(value["model_slot_contract"]["slot_cap"], 2)
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertFalse(value["authorization"]["additional_rollout_or_avg4"])
        self.assertFalse(value["authorization"]["leaderboard_submission_or_sota_claim"])

    def test_scheduler_runs_exact220_once_and_never_exceeds_four(self) -> None:
        tasks = [visible(position) for position in range(1, SELECTED_COUNT + 1)]
        seen: list[str] = []
        active = 0
        maximum = 0
        lock = threading.Lock()
        progress: list[dict] = []

        def fake(_root, _protocol, task, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(task["opaque_id"])
            time.sleep(0.001)
            with lock:
                active -= 1
            return runner.TaskOutcome(
                fallback(int(task["opaque_id"][5:], 16), self.limits), True, True, 0
            )

        outcomes = runner.execute_forward(
            ROOT,
            self.protocol,
            tasks,
            task_runner=fake,
            progress_writer=progress.append,
        )
        self.assertEqual(len(outcomes), SELECTED_COUNT)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual(len(seen), SELECTED_COUNT)
        self.assertEqual(len(set(seen)), SELECTED_COUNT)
        self.assertEqual(progress[-1]["completed_predictions"], SELECTED_COUNT)
        self.assertEqual(progress[-1]["unfinished_predictions"], 0)

    def test_forward_source_has_no_mapping_or_finalizer_capability(self) -> None:
        source = (ROOT / "scripts/run_v24266_exact220.py").read_text(encoding="utf-8")
        for forbidden in ("MAPPING_PATH", "evaluator_mapping", "finalize_v24266_exact220"):
            self.assertNotIn(forbidden, source)

    def test_worker_failure_is_terminal_fallback_in_denominator(self) -> None:
        value = fallback(1, self.limits)
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["completion_kind"], "worker_failure_fallback")
        row = runner._runtime_row(value)
        runner.validate_runtime_row(row)

    def test_progress_rejects_resealed_content_injection(self) -> None:
        value = runner._safe_forward_progress(17)
        runner.validate_progress(value)
        value["question"] = "forbidden"
        unsigned = dict(value)
        unsigned.pop("progress_payload_sha256")
        value["progress_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "progress schema"):
            runner.validate_progress(value)

    def test_evaluator_command_pins_identity_and_explicit_prefix_resume(self) -> None:
        command = finalizer.evaluator_command(ROOT, self.protocol, resume=True)
        self.assertIn("--resume", command)
        self.assertIn("--query-path", command)
        self.assertIn("--answer-root", command)
        self.assertNotIn("--instance-id", command)
        self.assertNotIn("--limit", command)

    def test_final_result_rejects_resealed_extra_field_before_file_reads(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24266_exact220_result",
            "protocol_id": self.protocol["protocol_id"],
            "created_at_unix": 1,
            "status": "exact220_single_rollout_complete",
            "selected": SELECTED_COUNT,
            "conservative_denominator": SELECTED_COUNT,
            "failure_as_zero": True,
            "exact220_prediction_freeze_before_evaluator": True,
            "metrics": {},
            "provenance": {},
            "source_policy": {},
            "authorization": {},
            "claims": {
                "public_exact220_single_rollout": True,
                "cold_execution": True,
                "unseen_or_held_out": False,
                "avg_at_4": False,
                "leaderboard_submitted": False,
                "sota": False,
            },
            "question": "forbidden",
        }
        value["result_payload_sha256"] = payload_sha256(value)
        with self.assertRaisesRegex(RuntimeError, "identity"):
            finalizer.validate_final_result(ROOT, self.protocol, value)

    def test_finalizer_validates_freeze_before_live_evaluator_identity(self) -> None:
        order: list[str] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            (root / finalizer.EVALUATOR_ROOT).mkdir(parents=True)
            with mock.patch.object(
                finalizer, "validate_protocol", return_value=self.protocol
            ), mock.patch.object(
                finalizer,
                "validate_forward_barrier",
                side_effect=lambda *_: order.append("freeze") or {},
            ), mock.patch.object(
                finalizer,
                "validate_live_evaluator_identity",
                side_effect=lambda *_: order.append("evaluator") or {},
            ), self.assertRaisesRegex(RuntimeError, "explicit recovery"):
                finalizer.finalize(root)
        self.assertEqual(order, ["freeze", "evaluator"])

    def test_activation_blocks_active_lease_without_process_signal(self) -> None:
        preaudit = {
            "role": "v24266_exact220_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
        }
        preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
        with mock.patch.object(activation_target, "validate_protocol", return_value=self.protocol), mock.patch.object(activation_target, "read_object", return_value=preaudit), mock.patch.object(activation_target, "sha256", return_value="a" * 64), mock.patch.object(activation_target, "process_snapshot", return_value=[]), mock.patch.object(activation_target, "lease_observation", return_value={"active": True}), self.assertRaisesRegex(RuntimeError, "boundary"):
            activation_target.build_activation(ROOT, now=1)

    def test_preaudit_blocks_active_lease_and_is_read_only(self) -> None:
        with mock.patch.object(audit_target, "validate_protocol", return_value=self.protocol), mock.patch.object(audit_target, "process_snapshot", return_value=[]), mock.patch.object(audit_target, "lease_observation", return_value={"active": True}), mock.patch.object(audit_target, "sha256", return_value="a" * 64):
            value = audit_target.build_report(ROOT, now=1)
        self.assertFalse(value["launch_authorized"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertFalse(value["network_model_search_fetch_or_evaluator_api_called_by_audit"])
        self.assertFalse(value["protected_existing_processes_signaled_restarted_or_stopped"])


if __name__ == "__main__":
    unittest.main()
