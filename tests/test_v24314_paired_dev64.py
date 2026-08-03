from __future__ import annotations

import inspect
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24267_total_fallback import build_total_fallback_result  # noqa: E402
from deepwide_agent.v24314_forward_contract import (  # noqa: E402
    ARMS,
    EXECUTOR_CONCURRENCY_PER_ARM,
    LIMITS,
    MODEL_SLOT_CAP,
    SELECTED_COUNT,
    TOTAL_EXECUTOR_CONCURRENCY,
    selected_tasks,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    zero_effect_receipt,
)
from scripts import finalize_v24314_paired_dev64 as finalizer  # noqa: E402
from scripts import preregister_v24314_paired_dev64 as prereg  # noqa: E402
from scripts import run_v24314_paired_dev64 as runner  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return one table. The column names are: Name, Version, Date.",
    }


class V24314PairedDev64Tests(unittest.TestCase):
    def test_preregistration_is_fresh_paired_and_label_blind(self) -> None:
        forward = prereg.build_forward_contract(ROOT, now=1, require_pristine=False)
        protocol = prereg.build_protocol(
            ROOT, forward=forward, now=1, require_pristine=False
        )
        self.assertEqual(forward["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(forward["execution"]["arms"], list(ARMS))
        self.assertEqual(forward["execution"]["executor_concurrency_per_arm"], 4)
        self.assertEqual(forward["execution"]["total_executor_concurrency"], 8)
        self.assertEqual(forward["execution"]["model_slot_cap"], MODEL_SLOT_CAP)
        self.assertEqual(MODEL_SLOT_CAP, 2)
        self.assertTrue(forward["comparison_contract"]["fresh_both_arms"])
        self.assertTrue(
            forward["comparison_contract"][
                "deadline_aware_transport_and_outer_totality_v24313"
            ]
        )
        self.assertEqual(
            protocol["decision_contract"][
                "minimum_valid_child_terminal_receipts_per_arm"
            ],
            64,
        )
        self.assertEqual(
            protocol["decision_contract"]["maximum_non_success_parent_exits_per_arm"],
            0,
        )
        self.assertTrue(
            forward["comparison_contract"][
                "both_arms_frozen_before_mapping_or_evaluator_open"
            ]
        )
        self.assertFalse(protocol["authorization"]["exact220_launch"])
        self.assertFalse(protocol["authorization"]["sota_claim"])
        self.assertTrue(
            protocol["evaluator_identity_parent"]["path"].startswith(
                "results/v24306_paired_dev64_preregistration"
            )
        )
        self.assertFalse(
            protocol["evaluator_identity_parent"][
                "historical_result_score_or_evaluator_output_opened"
            ]
        )
        self.assertNotIn(
            "_parent_evaluator_contract",
            inspect.getsource(prereg),
        )
        self.assertNotIn(
            "scripts/finalize_v24314_paired_dev64.py",
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
        summary = runner._summary(
            "baseline",
            [outcome.result for outcome in outcomes["baseline"]],
            [
                runner._runtime_row(outcome.result, "baseline")
                for outcome in outcomes["baseline"]
            ],
            outcomes["baseline"],
            0.01,
        )
        health = finalizer._arm_health(summary, "baseline")
        self.assertEqual(health["parent_exit_receipts_present"], 0)
        self.assertEqual(health["non_success_parent_exits"], SELECTED_COUNT)

    def test_real_synthetic_child_parent_success_and_nonzero_smoke(self) -> None:
        import tempfile

        fixture = ROOT / "tests/fixtures/v24314_synthetic_child.py"
        for mode in ("success", "nonzero"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(
                dir=ROOT / "outputs"
            ) as temporary:
                base = Path(temporary)
                relative = base.relative_to(ROOT)
                task_root = base / "tasks"
                arm_root = task_root / "baseline"
                arm_root.mkdir(parents=True)
                directory = arm_root / "task_0001"
                item = runner.WorkItem("baseline", 1, visible(1))

                def command(_root, _item, target):
                    return [
                        str(ROOT / ".venv-eval/bin/python"),
                        "-I",
                        "-B",
                        str(fixture),
                        "--mode",
                        mode,
                        "--arm",
                        "baseline",
                        "--task",
                        str(target / "visible_task.json"),
                        "--result",
                        str(target / "result.json"),
                        "--model-receipt",
                        str(target / runner.RECEIPT_NAME),
                        "--transport",
                        str(target / runner.TRANSPORT_NAME),
                        "--terminal",
                        str(target / "child_terminal_receipt.json"),
                    ]

                with mock.patch.object(runner, "OUTPUT_ROOT", relative), mock.patch.object(
                    runner, "TASK_ROOT", relative / "tasks"
                ), mock.patch.object(runner, "task_command", side_effect=command):
                    outcome = runner.run_one_task(ROOT, {}, item, directory)
                self.assertIsNotNone(outcome.parent_exit)
                self.assertTrue((directory / "parent_exit_receipt.json").is_file())
                if mode == "success":
                    self.assertEqual(
                        outcome.parent_exit["failure_taxonomy"], "success"
                    )
                    self.assertTrue(outcome.receipt_valid)
                    self.assertTrue(
                        outcome.result[RECEIPT_FIELD]["effect_count_complete"]
                    )
                    terminal_mtime = (
                        directory / "child_terminal_receipt.json"
                    ).stat().st_mtime_ns
                    for name in (
                        "result.json",
                        runner.RECEIPT_NAME,
                        runner.TRANSPORT_NAME,
                    ):
                        self.assertLessEqual(
                            (directory / name).stat().st_mtime_ns,
                            terminal_mtime,
                        )
                else:
                    self.assertEqual(
                        outcome.parent_exit["failure_taxonomy"],
                        "child_nonzero_with_terminal_receipt",
                    )
                    self.assertFalse(outcome.receipt_valid)
                    self.assertFalse(
                        outcome.result[RECEIPT_FIELD]["effect_count_complete"]
                    )
                    self.assertEqual(
                        outcome.result[RECEIPT_FIELD][
                            "admitted_model_effects_upper_bound"
                        ],
                        LIMITS["model_calls"],
                    )

    def test_decision_requires_quality_mechanism_and_both_arm_health(self) -> None:
        protocol = {
            "decision_contract": dict(prereg.DECISION_CONTRACT),
            "predecessor_efficiency_contract": {
                "v24306_shared_forward_wall_seconds": 1660.434161,
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
            "retrieval_completed": 64,
            "controller_stop": 50,
            "controller_expand": 14,
            "hosted_search_requests_added_by_reserved": 0,
            "cache_miss_count": 0,
            "cache_serve_network_fetches": 0,
            "hard_fetch_deadline_failures": 2,
            "fetch_helper_failures": 0,
            "recovery_enabled": 64,
            "effect_attribution_complete": 64,
            "effect_count_complete": 64,
            "provider_attempt_count_complete": 64,
            "synthesis_initial_model_request_error": 0,
            "synthesis_recovery_attempted": 0,
            "synthesis_recovery_succeeded": 0,
            "synthesis_recovery_model_request_error": 0,
            "repair_blocked_after_recovery": 0,
            "fourth_model_effect": 0,
            "total_model_effects_lower_bound": 128,
            "admitted_model_effects_upper_bound": 128,
            "unattributed_model_effects": 0,
            "parent_exit_receipts_present": 64,
            "parent_exit_receipts_valid": 64,
            "valid_child_terminal_receipts": 64,
            "model_slot_receipts_present": 64,
            "valid_model_slot_receipts": 64,
            "valid_transport_receipts": 64,
            "successful_parent_exits": 64,
            "non_success_parent_exits": 0,
            "incomplete_effect_counts": 0,
        }
        health = {
            "baseline": {
                **common,
                "reserved_stage_executed": 0,
                "low_coverage_diversity_tail": 0,
                "selected_tail_count": 0,
                "reserved_fetches": 0,
                "reserved_usable_pages": 0,
            },
            "candidate": {
                **common,
                "reserved_stage_executed": 14,
                "low_coverage_diversity_tail": 2,
                "selected_tail_count": 4,
                "reserved_fetches": 28,
                "reserved_usable_pages": 12,
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
            "zero": 30,
            "negative": 14,
            "minimum": -0.1,
            "maximum": 0.2,
            "percentile_95_interval": [-0.01, 0.02],
            "interval_width": 0.03,
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
                shared_forward_wall_seconds=1600.0,
            )["passed"]
        )
        bad = {arm: dict(value) for arm, value in health.items()}
        bad["candidate"]["low_coverage_diversity_tail"] = 0
        self.assertFalse(
            finalizer.decision(
                protocol,
                baseline,
                candidate,
                bad,
                uncertainty,
                shared_forward_wall_seconds=1600.0,
            )["passed"]
        )
        incomplete = {arm: dict(value) for arm, value in health.items()}
        incomplete["baseline"]["effect_count_complete"] = 61
        incomplete["baseline"]["incomplete_effect_counts"] = 3
        incomplete["baseline"]["effect_attribution_complete"] = 61
        incomplete["baseline"]["provider_attempt_count_complete"] = 61
        self.assertFalse(
            finalizer.decision(
                protocol,
                baseline,
                candidate,
                incomplete,
                uncertainty,
                shared_forward_wall_seconds=1600.0,
            )["passed"]
        )
        missing_parent = {arm: dict(value) for arm, value in health.items()}
        missing_parent["candidate"]["parent_exit_receipts_present"] = 63
        missing_parent["candidate"]["parent_exit_receipts_valid"] = 63
        missing_parent["candidate"]["valid_child_terminal_receipts"] = 63
        missing_parent["candidate"]["valid_model_slot_receipts"] = 63
        missing_parent["candidate"]["valid_transport_receipts"] = 63
        self.assertFalse(
            finalizer.decision(
                protocol,
                baseline,
                candidate,
                missing_parent,
                uncertainty,
                shared_forward_wall_seconds=1600.0,
            )["passed"]
        )

    def test_forward_has_no_evaluator_capability_and_lease_precedes_surface(self) -> None:
        source = (ROOT / "scripts/run_v24314_paired_dev64.py").read_text(encoding="utf-8")
        for forbidden in (
            "run_official_eval_local",
            "finalize_v24314_paired_dev64",
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

    def test_child_has_no_static_model_client_or_legacy_slot_limiter(self) -> None:
        source = (ROOT / "scripts/run_v24314_paired_dev64_task.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ResponsesClient(", source)
        self.assertNotIn("GlobalModelSlotLimiter(", source)
        self.assertIn("build_deadline_model(", source)
        self.assertIn("run_v24313_task(", source)

    def test_finalizer_validates_both_arm_barrier_before_evaluator(self) -> None:
        source = inspect.getsource(finalizer.finalize)
        self.assertLess(source.index("validate_candidate_barrier"), source.index("validate_live_evaluator_identity"))
        self.assertLess(source.index("validate_candidate_barrier"), source.index("prepare_arm"))
        self.assertLess(source.index("with acquire_deepwide_api_lease"), source.index("validate_live_evaluator_identity"))
        self.assertLess(source.index("with acquire_deepwide_api_lease"), source.index("mkdir"))
        self.assertEqual(finalizer.fixed_partitions(), [(0, 16), (16, 32), (32, 48), (48, 64)])

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
