from __future__ import annotations

import inspect
import json
import sys
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24267_total_fallback import build_total_fallback_result  # noqa: E402
from deepwide_agent.v24306_forward_contract import (  # noqa: E402
    ARMS,
    EXECUTOR_CONCURRENCY_PER_ARM,
    LIMITS,
    MODEL_SLOT_CAP,
    SELECTED_COUNT,
    TOTAL_EXECUTOR_CONCURRENCY,
    selected_tasks,
)
from deepwide_agent import v24303_forward_contract as predecessor  # noqa: E402
from deepwide_agent import v24306_forward_contract as contract  # noqa: E402
from deepwide_agent.v24306_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    zero_effect_receipt,
)
from scripts import finalize_v24306_paired_dev64 as finalizer  # noqa: E402
from scripts import preregister_v24306_paired_dev64 as prereg  # noqa: E402
from scripts import run_v24306_paired_dev64 as runner  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Version, Date.",
    }


class V24306PairedDev64Tests(unittest.TestCase):
    def test_predecessor_comparison_changes_only_global_model_slot_capacity(self) -> None:
        self.assertEqual(contract.MODEL, predecessor.MODEL)
        self.assertEqual(contract.SEARCH, predecessor.SEARCH)
        self.assertEqual(contract.LIMITS, predecessor.LIMITS)
        self.assertEqual(contract.TWO_WAVE_POLICY, predecessor.TWO_WAVE_POLICY)
        self.assertEqual(contract.RESERVE_POLICY, predecessor.RESERVE_POLICY)
        self.assertEqual(contract.SOURCE_MANIFEST, predecessor.SOURCE_MANIFEST)
        self.assertEqual(contract.ID_SOURCE, predecessor.ID_SOURCE)
        self.assertEqual(
            contract.EXECUTOR_CONCURRENCY_PER_ARM,
            predecessor.EXECUTOR_CONCURRENCY_PER_ARM,
        )
        self.assertEqual(
            contract.TOTAL_EXECUTOR_CONCURRENCY,
            predecessor.TOTAL_EXECUTOR_CONCURRENCY,
        )
        self.assertEqual(predecessor.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.MODEL_SLOT_CAP, 2)

    def test_preregistration_is_fresh_paired_and_label_blind(self) -> None:
        forward = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        protocol = prereg.build_protocol(
            ROOT, forward=forward, now=1, require_pristine=False
        )
        self.assertEqual(forward["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(forward["execution"]["arms"], list(ARMS))
        self.assertEqual(forward["execution"]["executor_concurrency_per_arm"], 4)
        self.assertEqual(forward["execution"]["total_executor_concurrency"], 8)
        self.assertEqual(forward["execution"]["model_slot_cap"], 2)
        self.assertTrue(forward["comparison_contract"]["fresh_both_arms"])
        self.assertIn("without synthesis recovery", forward["comparison_contract"]["baseline"])
        self.assertIn("bounded synthesis recovery", forward["comparison_contract"]["candidate"])
        self.assertIn("unused third", forward["comparison_contract"]["only_intended_treatment"])
        self.assertTrue(
            forward["comparison_contract"]["per_task_runtime_exact_v24303_alias"]
        )
        self.assertEqual(
            forward["comparison_contract"]["predecessor_v24303_model_slot_cap"],
            8,
        )
        self.assertEqual(
            forward["comparison_contract"]["current_model_slot_cap"], 2
        )
        self.assertTrue(
            forward["comparison_contract"][
                "both_arms_frozen_before_mapping_or_evaluator_open"
            ]
        )
        self.assertFalse(protocol["authorization"]["exact220_launch"])
        self.assertFalse(protocol["authorization"]["sota_claim"])
        self.assertNotIn(
            "scripts/finalize_v24306_paired_dev64.py",
            forward["dependency_manifest"],
        )

    def test_selected_tasks_are_exact_visible_dev64(self) -> None:
        forward = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        tasks = selected_tasks(ROOT, forward)
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), SELECTED_COUNT)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_scheduler_is_interleaved_exact_and_four_per_arm(self) -> None:
        tasks = [visible(position) for position in range(1, SELECTED_COUNT + 1)]
        limits = ScoreFirstLimits(**LIMITS)
        active = {arm: 0 for arm in ARMS}
        maximum = {arm: 0 for arm in ARMS}
        total_active = maximum_total = 0
        seen: list[tuple[str, int]] = []
        lock = threading.Lock()

        def fake(_root, _contract, item, _directory):
            nonlocal total_active, maximum_total
            with lock:
                active[item.arm] += 1
                total_active += 1
                maximum[item.arm] = max(maximum[item.arm], active[item.arm])
                maximum_total = max(maximum_total, total_active)
                seen.append((item.arm, item.position))
            time.sleep(0.001)
            with lock:
                active[item.arm] -= 1
                total_active -= 1
            result = build_total_fallback_result(
                item.task,
                limits=limits,
                completion_kind="worker_failure_fallback",
                failure_stage="test",
                failure_type="Synthetic",
                elapsed_seconds=0.01,
            )
            result[RECEIPT_FIELD] = zero_effect_receipt(item.arm)
            return runner.TaskOutcome(
                item.arm,
                item.position,
                result,
                False,
                False,
                0,
                {
                    "hard_fetch_helper_calls": 0,
                    "hard_fetch_deadline_failures": 0,
                    "fetch_helper_failures": 0,
                },
            )

        outcomes = runner.execute_forward(ROOT, {}, tasks, task_runner=fake)
        self.assertEqual({arm: len(outcomes[arm]) for arm in ARMS}, {arm: 64 for arm in ARMS})
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(maximum, {arm: EXECUTOR_CONCURRENCY_PER_ARM for arm in ARMS})
        self.assertEqual(maximum_total, TOTAL_EXECUTOR_CONCURRENCY)

    def test_parent_executor_fallback_has_exact_zero_effect_receipt(self) -> None:
        item = runner.WorkItem("candidate", 1, visible(1))
        value = runner._fallback(
            item,
            kind="worker_failure_fallback",
            failure="Synthetic",
            elapsed=0.0,
            progress={},
        )
        receipt = value[RECEIPT_FIELD]
        self.assertTrue(receipt["recovery_enabled"])
        self.assertEqual(receipt["total_effects_admitted"], 0)
        self.assertEqual(receipt["provider_requests_delta"], 0)
        self.assertFalse(receipt["fourth_model_effect"])

    def test_decision_requires_quality_mechanism_and_both_arm_health(self) -> None:
        protocol = {
            "decision_contract": dict(prereg.DECISION_CONTRACT),
            "predecessor_efficiency_contract": {
                "v24303_shared_forward_wall_seconds": prereg.PREDECESSOR_FORWARD_WALL_SECONDS
            },
        }
        baseline = {
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
        candidate = dict(baseline)
        candidate.update(
            {
                "quality_composite": 0.4455,
                "f1_by_item": 0.404,
                "column_f1": 0.488,
                "system_total_tokens": 2_050_000,
                "task_wall_sum_seconds": 3250.0,
            }
        )
        common = {
            "retrieval_completed": 64, "controller_stop": 50,
            "controller_expand": 14, "reserved_stage_executed": 14,
            "low_coverage_diversity_tail": 2, "selected_tail_count": 4,
            "reserved_fetches": 28, "reserved_usable_pages": 12,
            "hosted_search_requests_added_by_reserved": 0,
            "cache_miss_count": 0, "cache_serve_network_fetches": 0,
            "hard_fetch_deadline_failures": 2, "fetch_helper_failures": 0,
            "synthesis_initial_model_request_error": 2,
            "synthesis_recovery_model_request_error": 0,
            "repair_blocked_after_recovery": 0, "fourth_model_effect": 0,
            "total_model_effects": 128,
        }
        health = {
            "baseline": {
                **common, "recovery_enabled": 0,
                "synthesis_recovery_attempted": 0,
                "synthesis_recovery_succeeded": 0,
            },
            "candidate": {
                **common, "recovery_enabled": 64,
                "synthesis_recovery_attempted": 2,
                "synthesis_recovery_succeeded": 2,
                "total_model_effects": 130,
            },
        }
        uncertainty = {
            "task_count": 64,
            "bootstrap_unit": "paired_frozen_task",
            "seed": 24303,
            "resamples": 10_000,
            "estimand": "mean paired failure-as-zero quality composite delta on fresh dev64",
            "mean": 0.003,
            "median": 0.0,
            "positive": 20,
            "zero": 24,
            "negative": 20,
            "minimum": -0.2,
            "maximum": 0.3,
            "percentile_95_interval": [-0.04, 0.08],
            "interval_width": 0.12,
            "fixed_denominator_failure_as_zero": True,
            "predictions_frozen_before_evaluator": True,
            "confirmatory_development_gate": True,
            "future_population_or_sota_inference": False,
        }
        self.assertTrue(
            finalizer.decision(
                protocol,
                baseline,
                candidate,
                health,
                uncertainty,
                shared_forward_wall_seconds=1000.0,
            )["passed"]
        )
        bad = {arm: dict(values) for arm, values in health.items()}
        bad["candidate"]["synthesis_recovery_succeeded"] = 0
        self.assertFalse(
            finalizer.decision(
                protocol,
                baseline,
                candidate,
                bad,
                uncertainty,
                shared_forward_wall_seconds=1000.0,
            )["passed"]
        )

    def test_paired_uncertainty_is_task_clustered_and_deterministic(self) -> None:
        def summary(offset: float):
            return {
                "per_task": [
                    {
                        "opaque_id": f"task_{index:024x}",
                        "metrics": {
                            name: min(1.0, 0.2 + offset + (index % 5) * 0.01)
                            for name in finalizer.QUALITY
                        },
                    }
                    for index in range(64)
                ]
            }

        first = finalizer.paired_uncertainty(
            {"baseline": summary(0.0), "candidate": summary(0.01)},
            seed=24303,
            resamples=10_000,
        )
        second = finalizer.paired_uncertainty(
            {"baseline": summary(0.0), "candidate": summary(0.01)},
            seed=24303,
            resamples=10_000,
        )
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["mean"], 0.01)
        self.assertEqual(first["bootstrap_unit"], "paired_frozen_task")

    def test_forward_has_no_evaluator_capability_and_lease_precedes_surface(self) -> None:
        source = (ROOT / "scripts/run_v24306_paired_dev64.py").read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local",
            "finalize_v24306_paired_dev64",
            "evaluator_mapping",
            "MAPPING_PATH",
            "EVALUATOR_ROOT",
        ):
            self.assertNotIn(forbidden, source)
        main = inspect.getsource(runner.main)
        lease = main.index("with acquire_deepwide_api_lease")
        start = main.index("_new_json(root / EXECUTION_START")
        output = main.index("(root / OUTPUT_ROOT).mkdir")
        self.assertLess(lease, start)
        self.assertLess(lease, output)

    def test_finalizer_validates_both_arm_barrier_before_evaluator(self) -> None:
        source = inspect.getsource(finalizer.finalize)
        self.assertLess(source.index("validate_candidate_barrier"), source.index("validate_live_evaluator_identity"))
        self.assertLess(source.index("validate_candidate_barrier"), source.index("prepare_arm"))
        self.assertEqual(finalizer.fixed_partitions(), [(0, 16), (16, 32), (32, 48), (48, 64)])

    def test_current_protected_watchers_are_bound_by_pid_marker_and_start_ticks(self) -> None:
        from deepwide_agent.v24306_forward_contract import protected_watcher_snapshot

        snapshot = protected_watcher_snapshot()
        self.assertEqual({row["pid"] for row in snapshot}, {795336, 3061652})
        self.assertTrue(all(row["start_ticks"] > 0 for row in snapshot))
        self.assertTrue(
            all(row["marker"].startswith("scripts/watch_") for row in snapshot)
        )

    def test_parallel_evaluator_runs_four_exact16_workers_per_arm(self) -> None:
        import tempfile
        from types import SimpleNamespace
        from unittest import mock

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
            for arm in ARMS
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
                    json.dumps(
                        {
                            "instance_id": row["instance_id"],
                            "error": "Synthetic",
                            "elapsed_seconds": 0.01,
                        }
                    )
                    + "\n"
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
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            base = Path(directory).relative_to(ROOT)
            with mock.patch.object(finalizer, "EVALUATOR_ROOT", base), mock.patch.object(
                finalizer, "ARM_ROOTS", {arm: base / arm for arm in ARMS}
            ), mock.patch.object(
                finalizer, "RUNS", {arm: base / arm / "runs" for arm in ARMS}
            ), mock.patch.object(
                finalizer, "LOGS", {arm: base / arm / "logs" for arm in ARMS}
            ), mock.patch.object(
                finalizer, "MERGED", {arm: base / arm / "merged.jsonl" for arm in ARMS}
            ), mock.patch.object(
                finalizer, "MERGE", {arm: base / arm / "merge.json" for arm in ARMS}
            ), mock.patch.object(
                finalizer, "validate_live_evaluator_identity", return_value=projection
            ), mock.patch.object(
                finalizer,
                "validate_evaluator_contract",
                return_value={**projection, "run_contract_sha256": "r" * 64},
            ), mock.patch.object(finalizer, "acquire_deepwide_api_lease") as lease:
                lease.return_value.__enter__.return_value = {}
                lease.return_value.__exit__.return_value = False
                result = finalizer.run_all_evaluators(
                    ROOT, protocol, prepared, command_runner=fake_runner
                )
        self.assertEqual(set(result["arms"]), set(ARMS))
        self.assertTrue(
            all(len(result["arms"][arm]["rows"]) == SELECTED_COUNT for arm in ARMS)
        )


if __name__ == "__main__":
    unittest.main()
