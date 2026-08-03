from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24267_total_fallback import build_total_fallback_result  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24287_exact220_runtime import (  # noqa: E402
    run_v24287_task,
    validate_v24287_result,
)
from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
    validate_fetch_result,
)
from deepwide_agent.v24287_forward_contract import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    LIMITS,
    SELECTED_COUNT,
    TWO_WAVE_POLICY,
    source_selected_shards,
)
from scripts import finalize_v24287_exact220 as finalizer  # noqa: E402
from scripts import audit_v24287_exact220 as audit_target  # noqa: E402
from scripts import preregister_v24287_exact220 as preregister  # noqa: E402
from scripts import run_v24287_exact220 as runner  # noqa: E402
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Value, and Date.",
    }


class FakeModel:
    def __init__(self, values):
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class V24287Exact220Tests(unittest.TestCase):
    def test_preregistration_freezes_concurrency_boundary_and_no_extra_rollout(self) -> None:
        forward = preregister.build_forward_contract(ROOT, now=1, require_pristine=False)
        self.assertEqual(forward["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(forward["task_contract"]["selected_count"], SELECTED_COUNT)
        self.assertEqual(forward["execution"]["executor_concurrency"], 8)
        self.assertEqual(forward["execution"]["model_slot_cap"], 8)
        self.assertFalse(forward["execution"]["resume_skip_rerun_or_selective_retry"])
        self.assertFalse(forward["authorization"]["additional_rollout_or_rerun"])
        self.assertFalse(forward["source_policy"]["mapping_gold_category_question_type_split_evaluator_score_read_by_forward"])
        self.assertNotIn("scripts/finalize_v24287_exact220.py", forward["dependency_manifest"])

    def test_hard_fetch_url_is_stdin_only_and_total_timeout_kills_group(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        class GoodProcess:
            pid = 123456789
            returncode = 0

            def communicate(self, value, timeout=None):
                self.value = value
                self.timeout = timeout
                return (
                    '{"status":"ok","url":"https://example.com/final",'
                    '"title":"T","text":"body","links":[]}',
                    None,
                )

        good = GoodProcess()

        def good_popen(command, **kwargs):
            calls.append((list(command), dict(kwargs)))
            return good

        client = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=good_popen,
        )
        private_url = "https://example.com/path-not-for-argv"
        result = client._fetch_url(private_url)
        self.assertEqual(validate_fetch_result(result)["status"], "ok")
        self.assertNotIn(private_url, "\n".join(calls[0][0]))
        self.assertIn(private_url, good.value)
        self.assertEqual(good.timeout, 25)
        self.assertTrue(calls[0][1]["start_new_session"])

        class SlowProcess:
            pid = 123456789
            returncode = None

            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

            def wait(self, timeout=None):
                del timeout
                self.returncode = -15
                return self.returncode

        slow = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=lambda *args, **kwargs: SlowProcess(),
        )
        with mock.patch("os.killpg") as killpg:
            failed = slow._fetch_url("https://example.com/slow")
        self.assertEqual(failed["status"], "hard_deadline_exceeded")
        self.assertEqual(slow.hard_fetch_deadline_failures, 1)
        killpg.assert_called_once()

    def test_partition_is_exact_disjoint_52_52_52_64(self) -> None:
        shards = source_selected_shards(ROOT)
        self.assertEqual([(tag, len(ids)) for tag, ids in shards], [("test_s01", 52), ("test_s02", 52), ("test_s03", 52), ("devval", 64)])
        ids = [value for _, values in shards for value in values]
        self.assertEqual(len(ids), SELECTED_COUNT)
        self.assertEqual(len(set(ids)), SELECTED_COUNT)

    def test_runtime_normal_path_is_v24286_and_failure_is_total_fallback(self) -> None:
        task = visible(1)
        plan = json.dumps({"columns": ["wrong"], "queries": ["one", "two"]})
        table = "| Name | Value | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
        result = run_v24287_task(
            task,
            model=FakeModel([plan, table]),
            search=FakeSearch(),
            limits=ScoreFirstLimits(**LIMITS),
            policy=TwoWavePolicy(**TWO_WAVE_POLICY),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24287_result(result), "candidate")
        self.assertEqual(result["visible_schema"]["status"], "applied")
        failed = run_v24287_task(
            task,
            model=FakeModel([KeyboardInterrupt()]),
            search=FakeSearch(),
            limits=ScoreFirstLimits(**LIMITS),
            policy=TwoWavePolicy(**TWO_WAVE_POLICY),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24287_result(failed), "fallback")
        self.assertEqual(failed["status"], "completed")

    def test_candidate_tamper_cannot_be_reclassified_as_fallback(self) -> None:
        with self.assertRaisesRegex(ValueError, "neither candidate nor fallback"):
            validate_v24287_result(
                {"role": "v24286_visible_schema_timing_task_result", "completion_kind": "primary"}
            )

    def test_scheduler_runs_every_task_once_and_caps_at_eight(self) -> None:
        tasks = [visible(position) for position in range(1, SELECTED_COUNT + 1)]
        limits = ScoreFirstLimits(**LIMITS)
        active = maximum = 0
        seen: list[str] = []
        lock = threading.Lock()

        def fake(_root, _contract, task, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(task["opaque_id"])
            time.sleep(0.001)
            with lock:
                active -= 1
            result = build_total_fallback_result(
                task,
                limits=limits,
                completion_kind="worker_failure_fallback",
                failure_stage="test",
                failure_type="Synthetic",
                elapsed_seconds=0.01,
            )
            return runner.TaskOutcome(
                result,
                True,
                True,
                0,
                {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0},
            )

        outcomes = runner.execute_forward(ROOT, {}, tasks, task_runner=fake)
        self.assertEqual(len(outcomes), SELECTED_COUNT)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual(len(seen), len(set(seen)))

    def test_parallel_evaluator_partition_is_fixed_exact_and_disjoint(self) -> None:
        partitions = finalizer.fixed_partitions()
        self.assertEqual(len(partitions), 8)
        self.assertEqual(partitions[0][0], 0)
        self.assertEqual(partitions[-1][1], 220)
        flattened = [position for start, end in partitions for position in range(start, end)]
        self.assertEqual(flattened, list(range(220)))
        self.assertEqual([end - start for start, end in partitions], [28, 28, 28, 28, 27, 27, 27, 27])

    def test_parallel_evaluator_merges_every_fixed_error_row_once_in_original_order(self) -> None:
        official = [
            {"instance_id": f"instance_{position:03d}"}
            for position in range(SELECTED_COUNT)
        ]
        evaluator = {
            "query_data": {"path": "query.jsonl", "sha256": "q" * 64},
            "answer_corpus": {"root": "answers", "manifest_sha256": "a" * 64},
            "evaluator_source": {"manifest_sha256": "e" * 64},
            "judge": {
                "proxy_url": "http://127.0.0.1:9878/responses",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "low",
                "max_output_tokens": 8192,
                "timeout_seconds": 600,
                "max_retries": 12,
            },
            "recovery_policy": {
                "explicit_resume_required": True,
                "committed_success_or_error_is_terminal": True,
                "committed_rows_must_be_exact_prediction_prefix": True,
                "canonical_result_file_atomic_replace_per_task": True,
                "selective_error_retry_allowed": False,
            },
        }
        projection = {
            "query_data_sha256": evaluator["query_data"]["sha256"],
            "answer_corpus_manifest_sha256": evaluator["answer_corpus"]["manifest_sha256"],
            "evaluator_source_manifest_sha256": evaluator["evaluator_source"]["manifest_sha256"],
            "judge": evaluator["judge"],
            "recovery_policy": evaluator["recovery_policy"],
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            prediction_path = root / finalizer.OFFICIAL_PREDICTIONS
            prediction_path.parent.mkdir(parents=True)
            prediction_path.write_text(
                "".join(json.dumps(row) + "\n" for row in official),
                encoding="utf-8",
            )

            def fake_runner(command, **kwargs):
                del kwargs
                out = Path(command[command.index("--out-dir") + 1])
                source = Path(command[command.index("--predictions") + 1])
                ids = [
                    json.loads(line)["instance_id"]
                    for line in source.read_text(encoding="utf-8").splitlines()
                    if line
                ]
                out.mkdir(parents=True)
                (out / "run_config.json").write_text("{}\n", encoding="utf-8")
                (out / "official_eval_results.jsonl").write_text(
                    "".join(
                        json.dumps(
                            {
                                "instance_id": instance_id,
                                "error": "SyntheticEvaluatorError",
                                "elapsed_seconds": 0.01,
                            }
                        )
                        + "\n"
                        for instance_id in ids
                    ),
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0)

            with mock.patch.object(finalizer, "validate_evaluator_contract", return_value=projection):
                rows, evidence = finalizer.run_parallel_evaluator(
                    root,
                    {"evaluator_contract": evaluator},
                    official,
                    command_runner=fake_runner,
                )
        self.assertEqual([row["instance_id"] for row in rows], [row["instance_id"] for row in official])
        self.assertEqual(len(rows), SELECTED_COUNT)
        self.assertTrue(evidence["attestation"]["all_frozen_predictions_evaluated_exactly_once"])
        self.assertFalse(evidence["attestation"]["selective_retry_or_revaluation"])

    def test_forward_runner_has_no_evaluator_side_import_or_mapping(self) -> None:
        source = (ROOT / "scripts/run_v24287_exact220.py").read_text(encoding="utf-8")
        for forbidden in ("evaluator_mapping", "run_official_eval_local", "finalize_v24287_exact220"):
            self.assertNotIn(forbidden, source)

    def test_hard_deadline_fallback_remains_in_fixed_denominator_without_receipt(self) -> None:
        result = build_total_fallback_result(
            visible(1),
            limits=ScoreFirstLimits(**LIMITS),
            completion_kind="hard_deadline_fallback",
            failure_stage="test",
            failure_type="HardDeadlineExceeded",
            elapsed_seconds=195.0,
        )
        outcome = runner.TaskOutcome(
            result,
            False,
            False,
            0,
            {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0},
        )
        row = runner._runtime_row(outcome.result)
        runner.validate_runtime_row(row)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["completion_kind"], "hard_deadline_fallback")

    def test_read_only_audit_sees_only_allowed_provider_rank_access(self) -> None:
        contract = {
            "dependency_manifest": {
                "src/deepwide_agent/clients.py": "ignored",
                "scripts/run_v24287_exact220.py": "ignored",
            },
            "dependency_manifest_sha256": "a" * 64,
        }
        protocol = {"control_manifest_sha256": "b" * 64}
        with mock.patch.object(audit_target, "validate_forward_contract", return_value=contract), mock.patch.object(
            audit_target, "validate_protocol", return_value=protocol
        ), mock.patch.object(audit_target, "process_snapshot", return_value=[]), mock.patch.object(
            audit_target, "lease_observation", return_value={"active": False}
        ), mock.patch.object(audit_target, "sha256", return_value="c" * 64):
            value = audit_target.build_report(ROOT, now=1)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["launch_authorized"])
        self.assertTrue(value["unexpected_benchmark_privileged_field_accesses_absent"])
        self.assertEqual(value["allowed_provider_result_rank_accesses"], ["src/deepwide_agent/clients.py:565:score"])


if __name__ == "__main__":
    unittest.main()
