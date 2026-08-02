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
from deepwide_agent.v24265_paired_normalizer_runtime import (  # noqa: E402
    build_paired_fallback_result,
    validate_paired_result,
)
from scripts import activate_v24265_paired_dev64 as activation_target  # noqa: E402
from scripts import audit_v24265_paired_dev64 as audit_target  # noqa: E402
from scripts import finalize_v24265_paired_dev64 as finalizer  # noqa: E402
from scripts import run_v24265_paired_dev64 as runner  # noqa: E402
from scripts.preregister_v24265_paired_dev64 import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    MODEL_SLOT_CAP,
    SELECTED_COUNT,
    build_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def task(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return a Markdown table. Column names: Name, Value.",
    }


def fallback(position: int, limits: ScoreFirstLimits) -> dict:
    value = build_paired_fallback_result(
        task(position),
        limits=limits,
        completion_kind="worker_failure_fallback",
        failure_stage="test_executor",
        failure_type="SyntheticFailure",
        elapsed_seconds=0.1,
    )
    validate_paired_result(value)
    return value


def official_row(instance_id: str, prediction: str) -> dict:
    question = "visible question"
    return {
        "instance_id": instance_id,
        "question": question,
        "rollout_id": 1,
        "prediction": prediction,
        "messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": prediction},
        ],
    }


class V24265PairedDev64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = build_protocol(ROOT, now=1, require_pristine=False)
        cls.limits = ScoreFirstLimits(**dict(cls.protocol["limits"]))

    def test_protocol_freezes_exact64_four_by_two_and_label_blind_boundary(self) -> None:
        value = self.protocol
        self.assertEqual(value["task_contract"]["selected_count"], SELECTED_COUNT)
        self.assertEqual(value["forward_contract"]["executor_concurrency"], 4)
        self.assertEqual(value["model_slot_contract"]["slot_cap"], 2)
        self.assertEqual(
            value["task_contract"]["runtime_boundary"], ["opaque_id", "question"]
        )
        self.assertTrue(
            value["freeze_contract"]["both_exact_64_before_evaluator_side_open"]
        )
        self.assertFalse(value["authorization"]["full220_launch"])
        self.assertFalse(value["authorization"]["leaderboard_submission_or_sota_claim"])
        evaluator = value["evaluator_contract"]
        self.assertEqual(
            set(evaluator["query_data"]), {"path", "sha256"}
        )
        self.assertEqual(
            set(evaluator["answer_corpus"]), {"root", "manifest_sha256"}
        )
        self.assertFalse(
            evaluator["mapping_query_answer_or_gold_bytes_opened_or_hashed"]
        )

    def test_exact64_scheduler_never_exceeds_four_and_runs_each_task_once(self) -> None:
        tasks = [task(position) for position in range(1, SELECTED_COUNT + 1)]
        seen: list[str] = []
        lock = threading.Lock()
        active = 0
        maximum = 0
        progress: list[dict] = []

        def fake_task(_root, _protocol, visible, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(visible["opaque_id"])
            time.sleep(0.002)
            with lock:
                active -= 1
            return runner.TaskOutcome(fallback(int(visible["opaque_id"][5:], 16), self.limits), True, True, 0)

        outcomes = runner.execute_forward(
            ROOT,
            self.protocol,
            tasks,
            task_runner=fake_task,
            progress_writer=progress.append,
        )
        self.assertEqual(len(outcomes), SELECTED_COUNT)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual(sorted(seen), sorted(row["opaque_id"] for row in tasks))
        self.assertEqual(len(set(seen)), SELECTED_COUNT)
        self.assertEqual(progress[-1]["completed_pairs"], SELECTED_COUNT)
        self.assertEqual(progress[-1]["unfinished_pairs"], 0)

    def test_receipt_summary_binds_acquisitions_to_shared_requests(self) -> None:
        values = [
            runner.TaskOutcome(fallback(position, self.limits), True, True, 0)
            for position in range(1, SELECTED_COUNT + 1)
        ]
        healthy = runner._receipt_summary(values)
        self.assertTrue(healthy["all_acquisitions_match_actual_requests"])
        drifted = list(values)
        drifted[0] = runner.TaskOutcome(drifted[0].result, True, True, 1)
        self.assertFalse(
            runner._receipt_summary(drifted)[
                "all_acquisitions_match_actual_requests"
            ]
        )

    def test_worker_and_receipt_failures_return_two_terminal_fallbacks(self) -> None:
        value = fallback(1, self.limits)
        self.assertEqual(value["control"]["status"], "completed")
        self.assertEqual(value["candidate"]["status"], "completed")
        self.assertEqual(value["control"]["completion_kind"], "worker_failure_fallback")
        self.assertEqual(value["candidate"]["completion_kind"], "worker_failure_fallback")
        self.assertEqual(value["control"]["prediction"], value["candidate"]["prediction"])

    def test_forward_runner_has_no_mapping_or_finalizer_capability(self) -> None:
        source = (ROOT / "scripts/run_v24265_paired_dev64.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("MAPPING_PATH", source)
        self.assertNotIn("finalize_v24265_paired_dev64", source)
        self.assertNotIn("evaluator_mapping", source)

    def test_identical_prediction_reuse_requires_exact_evaluator_identity(self) -> None:
        control = [official_row("instance_1", "same")]
        candidate = [copy.deepcopy(control[0])]
        changed, identical = finalizer.partition_candidate_predictions(
            control, candidate
        )
        self.assertEqual(changed, [])
        self.assertEqual(identical, ["instance_1"])
        drifted = copy.deepcopy(candidate)
        drifted[0]["rollout_id"] = 2
        with self.assertRaisesRegex(RuntimeError, "identity"):
            finalizer.partition_candidate_predictions(control, drifted)

    def test_changed_prediction_is_evaluated_and_resume_is_explicit(self) -> None:
        control = [official_row("instance_1", "old")]
        candidate = [official_row("instance_1", "new")]
        changed, identical = finalizer.partition_candidate_predictions(
            control, candidate
        )
        self.assertEqual(changed, candidate)
        self.assertEqual(identical, [])
        command = finalizer.evaluator_command(
            ROOT,
            self.protocol,
            Path("predictions.jsonl"),
            Path("evaluator"),
            resume=True,
        )
        self.assertIn("--resume", command)
        self.assertIn("--query-path", command)
        self.assertIn("--answer-root", command)

    def _frozen_fixture(self, root: Path) -> tuple[dict, dict, dict, dict]:
        ids = [task(position)["opaque_id"] for position in range(1, SELECTED_COUNT + 1)]
        protocol = {
            "protocol_id": "test_protocol",
            "task_contract": {"selected_opaque_ids_sha256": payload_sha256(ids)},
        }
        results = [fallback(position, self.limits) for position in range(1, SELECTED_COUNT + 1)]
        control_rows = [runner._runtime_row(value, "control") for value in results]
        candidate_rows = [runner._runtime_row(value, "candidate") for value in results]
        control_runtime = root / "control.jsonl"
        candidate_runtime = root / "candidate.jsonl"
        runner._write_jsonl_new(control_runtime, control_rows)
        runner._write_jsonl_new(candidate_runtime, candidate_rows)
        control_summary = runner._summary(results, "control")
        candidate_summary = runner._summary(results, "candidate")
        control_summary_path = root / "control_summary.json"
        candidate_summary_path = root / "candidate_summary.json"
        control_summary_path.write_text(json.dumps(control_summary), encoding="utf-8")
        candidate_summary_path.write_text(json.dumps(candidate_summary), encoding="utf-8")
        control_freeze = runner._freeze(
            protocol, "control", control_runtime, control_summary_path
        )
        candidate_freeze = runner._freeze(
            protocol, "candidate", candidate_runtime, candidate_summary_path
        )
        return protocol, control_freeze, candidate_freeze, {
            "control_runtime": control_runtime,
            "candidate_runtime": candidate_runtime,
            "control_summary": control_summary_path,
            "candidate_summary": candidate_summary_path,
        }

    def test_freeze_and_progress_reject_resealed_content_injection(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            protocol, control, _candidate, paths = self._frozen_fixture(root)
            control["question"] = "forbidden"
            unsigned = dict(control)
            unsigned.pop("freeze_payload_sha256")
            control["freeze_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "freeze"):
                runner.validate_freeze(
                    control,
                    protocol=protocol,
                    arm="control",
                    runtime_path=paths["control_runtime"],
                    summary_path=paths["control_summary"],
                )
        progress = runner._safe_forward_progress(1, SELECTED_COUNT - 1)
        progress["question"] = "forbidden"
        unsigned = dict(progress)
        unsigned.pop("progress_payload_sha256")
        progress["progress_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "progress schema"):
            runner.validate_progress(progress)

    def test_arm_schema_rejects_extra_field_even_without_outer_tamper(self) -> None:
        value = fallback(1, self.limits)
        value["control"]["question"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "arm schema"):
            validate_paired_result(value)

    def test_activation_blocks_active_lease_without_signaling_existing_processes(self) -> None:
        preaudit = {
            "role": "v24265_paired_dev64_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
        }
        preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
        with mock.patch.object(
            activation_target, "validate_protocol", return_value=self.protocol
        ), mock.patch.object(
            activation_target, "read_object", return_value=preaudit
        ), mock.patch.object(
            activation_target, "sha256", return_value="a" * 64
        ), mock.patch.object(
            activation_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            activation_target, "lease_observation", return_value={"active": True}
        ), self.assertRaisesRegex(RuntimeError, "boundary"):
            activation_target.build_activation(ROOT, now=1)

    def test_preaudit_is_read_only_and_blocks_active_lease(self) -> None:
        with mock.patch.object(
            audit_target, "validate_protocol", return_value=self.protocol
        ), mock.patch.object(
            audit_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            audit_target, "lease_observation", return_value={"active": True}
        ), mock.patch.object(
            audit_target, "sha256", return_value="a" * 64
        ):
            value = audit_target.build_report(ROOT, now=1)
        self.assertFalse(value["launch_authorized"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertFalse(
            value["network_model_search_fetch_or_evaluator_api_called_by_audit"]
        )
        self.assertFalse(value["protected_existing_processes_signaled_restarted_or_stopped"])


if __name__ == "__main__":
    unittest.main()
