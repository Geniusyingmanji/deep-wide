from __future__ import annotations

import inspect
import json
import math
import tempfile
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24267_total_fallback import build_total_fallback_result  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24289_low_coverage_rescue import RescuePolicy  # noqa: E402
from deepwide_agent.v24291_dev64_runtime import run_v24291_task, validate_v24291_result  # noqa: E402
from deepwide_agent.v24291_forward_contract import (  # noqa: E402
    EXECUTOR_CONCURRENCY,
    LIMITS,
    MODEL_SLOT_CAP,
    RESCUE_POLICY,
    SELECTED_COUNT,
    TWO_WAVE_POLICY,
    selected_tasks,
)
from scripts import finalize_v24291_dev64 as finalizer  # noqa: E402
from scripts import preregister_v24291_dev64 as prereg  # noqa: E402
from scripts import run_v24291_dev64 as runner  # noqa: E402
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


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


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Version, and Date.",
    }


class V24291Dev64Tests(unittest.TestCase):
    def test_preregistration_freezes_full64_boundary_and_quality_gate(self) -> None:
        forward = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        protocol = prereg.build_protocol(ROOT, forward=forward, now=1, require_pristine=False)
        self.assertEqual(forward["task_contract"]["selected_count"], SELECTED_COUNT)
        self.assertEqual(forward["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(forward["execution"]["executor_concurrency"], 8)
        self.assertEqual(forward["execution"]["model_slot_cap"], 8)
        self.assertFalse(forward["execution"]["resume_skip_rerun_or_selective_retry"])
        self.assertEqual(protocol["comparison_contract"]["fixed_denominator_per_arm"], 64)
        self.assertTrue(protocol["comparison_contract"]["failure_as_zero"])
        self.assertEqual(protocol["evaluator_execution"]["fixed_contiguous_partition_sizes_per_arm"], [16, 16, 16, 16])
        self.assertEqual(protocol["decision_contract"], prereg.DECISION_CONTRACT)
        self.assertFalse(protocol["authorization"]["exact220_launch"])
        self.assertFalse(protocol["authorization"]["sota_claim"])
        self.assertNotIn("scripts/finalize_v24291_dev64.py", forward["dependency_manifest"])

    def test_selected_tasks_are_exact_frozen_devval64_visible_only(self) -> None:
        forward = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        tasks = selected_tasks(ROOT, forward)
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), SELECTED_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_runtime_normal_rescue_path_and_total_fallback(self) -> None:
        plan = json.dumps(
            {
                "columns": ["wrong"],
                "queries": ["visible one", "visible two", "visible three", "visible four"],
            }
        )
        table = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
        result = run_v24291_task(
            visible(1),
            model=FakeModel([plan, table]),
            search=TailSearch(sparse=True, failed_fetches=3, empty_first=True),
            limits=ScoreFirstLimits(**LIMITS),
            two_wave_policy=TwoWavePolicy(**TWO_WAVE_POLICY),
            rescue_policy=RescuePolicy(**RESCUE_POLICY),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24291_result(result), "candidate")
        self.assertTrue(result["two_wave_retrieval"]["receipt"]["rescue"]["triggered"])
        failed = run_v24291_task(
            visible(2),
            model=FakeModel([KeyboardInterrupt()]),
            search=TailSearch(sparse=False),
            limits=ScoreFirstLimits(**LIMITS),
            two_wave_policy=TwoWavePolicy(**TWO_WAVE_POLICY),
            rescue_policy=RescuePolicy(**RESCUE_POLICY),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24291_result(failed), "fallback")
        self.assertEqual(failed["completion_kind"], "worker_failure_fallback")

    def test_scheduler_runs_exact64_once_and_caps_at_eight(self) -> None:
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
                False,
                False,
                0,
                {"hard_fetch_helper_calls": 0, "hard_fetch_deadline_failures": 0, "fetch_helper_failures": 0},
            )

        outcomes = runner.execute_forward(ROOT, {}, tasks, task_runner=fake)
        self.assertEqual(len(outcomes), SELECTED_COUNT)
        self.assertEqual(maximum, EXECUTOR_CONCURRENCY)
        self.assertEqual(len(seen), len(set(seen)))

    def test_parallel_evaluator_partition_is_fixed_exact64_per_arm(self) -> None:
        self.assertEqual(finalizer.fixed_partitions(), [(0, 16), (16, 32), (32, 48), (48, 64)])
        self.assertEqual(prereg.EVALUATOR_WORKERS_PER_ARM * 2, prereg.TOTAL_EVALUATOR_WORKERS)

    def test_parallel_evaluator_merges_each_arm_exactly_once(self) -> None:
        protocol = {
            "evaluator_contract": {
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
            },
            "lease_contract": {
                "path": "outputs/deepwide_benchmark_api.lease.lock",
                "evaluator_owner": "test-owner",
                "evaluator_purpose": "test-purpose",
            },
        }
        prepared = {
            arm: {
                "official": [
                    {"instance_id": f"{arm}_{position:03d}"}
                    for position in range(SELECTED_COUNT)
                ]
            }
            for arm in finalizer.ARMS
        }

        def fake_runner(command, **kwargs):
            del kwargs
            output = Path(command[command.index("--out-dir") + 1])
            source = Path(command[command.index("--predictions") + 1])
            rows = [json.loads(line) for line in source.read_text().splitlines() if line]
            output.mkdir(parents=True)
            (output / "run_config.json").write_text("{}\n")
            (output / "official_eval_results.jsonl").write_text(
                "".join(
                    json.dumps({"instance_id": row["instance_id"], "error": "Synthetic", "elapsed_seconds": 0.01}) + "\n"
                    for row in rows
                )
            )
            return SimpleNamespace(returncode=0)

        projection = {
            "mapping_sha256": "m" * 64,
            "query_data_sha256": "q" * 64,
            "answer_corpus_manifest_sha256": "a" * 64,
            "evaluator_source_manifest_sha256": "e" * 64,
            "judge": protocol["evaluator_contract"]["judge"],
            "recovery_policy": protocol["evaluator_contract"]["recovery_policy"],
        }
        from unittest import mock

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory, mock.patch.multiple(
            finalizer,
            EVALUATOR_ROOT=Path(directory).relative_to(ROOT),
        ), mock.patch.object(finalizer, "ARM_ROOTS", {arm: Path(directory).relative_to(ROOT) / arm for arm in finalizer.ARMS}), mock.patch.object(
            finalizer, "RUNS", {arm: Path(directory).relative_to(ROOT) / arm / "runs" for arm in finalizer.ARMS}
        ), mock.patch.object(finalizer, "LOGS", {arm: Path(directory).relative_to(ROOT) / arm / "logs" for arm in finalizer.ARMS}), mock.patch.object(
            finalizer, "MERGED", {arm: Path(directory).relative_to(ROOT) / arm / "merged.jsonl" for arm in finalizer.ARMS}
        ), mock.patch.object(finalizer, "MERGE", {arm: Path(directory).relative_to(ROOT) / arm / "merge.json" for arm in finalizer.ARMS}), mock.patch.object(
            finalizer, "validate_live_evaluator_identity", return_value=projection
        ), mock.patch.object(finalizer, "validate_evaluator_contract", return_value={**projection, "run_contract_sha256": "r" * 64}), mock.patch.object(
            finalizer, "acquire_deepwide_api_lease"
        ) as lease:
            lease.return_value.__enter__.return_value = {}
            lease.return_value.__exit__.return_value = False
            result = finalizer.run_all_evaluators(ROOT, protocol, prepared, command_runner=fake_runner)
        self.assertEqual(set(result["arms"]), {"control", "candidate"})
        for arm in finalizer.ARMS:
            rows = result["arms"][arm]["rows"]
            self.assertEqual(len(rows), SELECTED_COUNT)
            self.assertEqual([row["instance_id"] for row in rows], [row["instance_id"] for row in prepared[arm]["official"]])
            self.assertFalse(result["arms"][arm]["attestation"]["selective_retry_or_error_revaluation"])

    def test_decision_requires_quality_gain_and_all_health_gates(self) -> None:
        protocol = {"decision_contract": dict(prereg.DECISION_CONTRACT)}
        base = {
            "runtime_completed": 64,
            "runtime_failed": 0,
            "evaluator_valid": 62,
            "evaluator_invalid_or_not_run": 2,
            "whole_table_successes": 4,
            "entity_acc": 0.65,
            "f1_by_row": 0.24,
            "f1_by_item": 0.40,
            "column_f1": 0.48,
            "quality_composite": 0.4425,
            "score": 0.0625,
            "model_generated_tables": 64,
            "fallback_tables": 0,
            "system_total_tokens": 2_000_000,
            "task_wall_sum_seconds": 3200.0,
        }
        candidate = dict(base)
        candidate.update(
            {
                "quality_composite": base["quality_composite"] + 0.003,
                "entity_acc": base["entity_acc"],
                "f1_by_row": base["f1_by_row"],
                "f1_by_item": base["f1_by_item"] + 0.004,
                "column_f1": base["column_f1"] + 0.008,
                "system_total_tokens": 2_100_000,
                "task_wall_sum_seconds": 3400.0,
            }
        )
        health = {
            "retrieval_completed": 64,
            "controller_stop": 50,
            "controller_expand": 14,
            "rescue_triggered": 4,
            "rescue_fetches": 12,
            "rescue_usable_pages": 10,
            "hosted_search_requests_added_by_rescue": 0,
            "cache_miss_count": 0,
            "cache_serve_network_fetches": 0,
            "hard_fetch_deadline_failures": 2,
            "fetch_helper_failures": 0,
        }
        decision = finalizer.decision(protocol, base, candidate, health)
        self.assertTrue(decision["passed"])
        degraded = dict(candidate)
        degraded["quality_composite"] = base["quality_composite"]
        self.assertFalse(finalizer.decision(protocol, base, degraded, health)["passed"])

    def test_metric_and_health_validation_rejects_nonfinite_or_malformed_counts(self) -> None:
        metrics = {
            "runtime_completed": 64,
            "runtime_failed": 0,
            "evaluator_valid": 62,
            "evaluator_invalid_or_not_run": 2,
            "whole_table_successes": 4,
            "entity_acc": 0.65,
            "f1_by_row": 0.24,
            "f1_by_item": 0.40,
            "column_f1": 0.48,
            "quality_composite": 0.4425,
            "score": 0.0625,
            "model_generated_tables": 64,
            "fallback_tables": 0,
            "system_total_tokens": 2_000_000,
            "task_wall_sum_seconds": 3200.0,
        }
        finalizer.validate_arm_metrics(metrics)
        bad = dict(metrics)
        bad["system_total_tokens"] = True
        with self.assertRaises(RuntimeError):
            finalizer.validate_arm_metrics(bad)
        bad = dict(metrics)
        bad["task_wall_sum_seconds"] = math.inf
        with self.assertRaises(RuntimeError):
            finalizer.validate_arm_metrics(bad)
        health = {
            "retrieval_completed": 64,
            "controller_stop": 50,
            "controller_expand": 14,
            "rescue_triggered": 4,
            "rescue_fetches": 12,
            "rescue_usable_pages": 10,
            "hosted_search_requests_added_by_rescue": 0,
            "cache_miss_count": 0,
            "cache_serve_network_fetches": 0,
            "hard_fetch_deadline_failures": 2,
            "fetch_helper_failures": 0,
        }
        finalizer.validate_candidate_health(health)
        bad_health = dict(health)
        bad_health["controller_expand"] = 13
        with self.assertRaises(RuntimeError):
            finalizer.validate_candidate_health(bad_health)

    def test_final_result_validation_recomputes_full_lineage(self) -> None:
        source = inspect.getsource(finalizer.validate_final_result)
        for required in (
            "validate_protocol",
            "validate_candidate_barrier",
            "load_control_after_candidate",
            "validate_prepared_arm",
            "validate_evaluator_merge",
            "validate_arm_summary",
            "expected_control",
            "expected_candidate",
            "expected_decision",
            "expected_provenance",
        ):
            self.assertIn(required, source)
        self.assertNotIn('decision(protocol, value["control"]', source)

    def test_control_projection_validates_aggregate_result_and_postresult_audit(self) -> None:
        source = inspect.getsource(finalizer.load_control_after_candidate)
        for required in (
            "validate_control_final_result",
            "CONTROL_RESULT",
            "CONTROL_POSTAUDIT",
            "aggregate_result_sha256",
            "postresult_audit_sha256",
            "audit_payload_sha256",
        ):
            self.assertIn(required, source)

    def test_merge_validator_binds_each_worker_and_rebuilds_merged_rows(self) -> None:
        source = inspect.getsource(finalizer.validate_evaluator_merge)
        for required in (
            "fixed_partitions",
            "worker_reports",
            "worker_{worker:02d}_predictions.jsonl",
            "validate_committed_eval_rows",
            "validate_evaluator_contract",
            "prediction_shard_sha256",
            "results_sha256",
            "run_config_sha256",
            "run_contract_sha256",
            "log_sha256",
            "merged != merged_from_workers",
        ):
            self.assertIn(required, source)

    def test_finalizer_validates_candidate_before_control_or_evaluator(self) -> None:
        source = inspect.getsource(finalizer.finalize)
        self.assertLess(source.index("validate_candidate_barrier"), source.index("load_control_after_candidate"))
        self.assertLess(source.index("validate_candidate_barrier"), source.index("validate_live_evaluator_identity"))
        self.assertLess(source.index("load_control_after_candidate"), source.index("prepare_arm"))

    def test_forward_acquires_shared_lease_before_publishing_run_surface(self) -> None:
        source = inspect.getsource(runner.main)
        lease = source.index("with acquire_deepwide_api_lease")
        execution_start = source.index("_new_json(root / EXECUTION_START")
        output_root = source.index("(root / OUTPUT_ROOT).mkdir")
        execute = source.index("outcomes = execute_forward")
        self.assertLess(lease, execution_start)
        self.assertLess(lease, output_root)
        self.assertLess(output_root, execute)

    def test_forward_validators_bind_execution_start_rows_and_task_receipts(self) -> None:
        forward_source = inspect.getsource(runner.validate_forward_result)
        freeze_source = inspect.getsource(runner.validate_prediction_freeze)
        for required in (
            "validate_execution_start",
            "execution_start_sha256",
            "RECEIPT_NAME",
            "validate_receipt",
            "expected_requests",
            "expected_acquisitions",
        ):
            self.assertIn(required, forward_source)
        self.assertIn("_summary_from_frozen_rows", freeze_source)

    def test_summary_validation_rejects_malformed_completion_kind_counts(self) -> None:
        summary = {
            "artifact_version": 1,
            "role": "v24291_dev64_run_summary",
            "selected": 64,
            "completed": 64,
            "failed": 0,
            "model_generated_tables": 64,
            "fallback_tables": 0,
            "completion_kinds": {"primary": 64},
            "system_total_tokens": 1,
            "task_wall_seconds_sum": 1.0,
            "forward_wall_seconds": 1.0,
            "hard_fetch_helper_calls": 0,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
            "rescue_totals": {
                "retrieval_completed": 64,
                "controller_stop": 64,
                "controller_expand": 0,
                "rescue_triggered": 0,
                "rescue_fetches": 0,
                "rescue_usable_pages": 0,
                "hosted_search_requests_added_by_rescue": 0,
                "cache_miss_count": 0,
                "cache_serve_network_fetches": 0,
            },
            "label_blind": True,
            "official_evaluator_called": False,
        }
        runner.validate_summary(summary)
        bad = dict(summary)
        bad["completion_kinds"] = {"primary": "64"}
        with self.assertRaises(RuntimeError):
            runner.validate_summary(bad)

    def test_forward_runner_has_no_control_or_evaluator_side_import(self) -> None:
        source = (ROOT / "scripts/run_v24291_dev64.py").read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local",
            "finalize_v24291_dev64",
            "evaluator_mapping",
            "CONTROL_RUNTIME",
            "CONTROL_PREDICTION_FREEZE",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
