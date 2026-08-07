from __future__ import annotations

import copy
import hashlib
import json
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent import v24780_staged_fallback_execution_contract as contract  # noqa: E402
from scripts import run_v24780_staged_fallback_external as runner  # noqa: E402
from scripts import run_v24780_staged_fallback_task as child  # noqa: E402
from deepwide_agent import v24778_staged_fetch_fallback_runtime as runtime  # noqa: E402
from deepwide_agent import v24309_runner_exit_integration as observed  # noqa: E402


def _successful_result(task: dict[str, str]) -> dict:
    entities = contract.visible_entities(task["question"])
    baseline = (
        "```markdown\n| Organization | Founded | Country |\n"
        "| --- | --- | --- |\n"
        + "\n".join(f"| {entity} | Unknown | Unknown |" for entity in entities)
        + "\n```"
    )
    candidate = (
        "```markdown\n| Organization | Founded | Country |\n"
        "| --- | --- | --- |\n"
        + "\n".join(
            f"| {entity} | {'2001' if index == 0 else 'Unknown'} | "
            f"{'France' if index == 1 else 'Unknown'} |"
            for index, entity in enumerate(entities)
        )
        + "\n```"
    )
    predictions = {"baseline": baseline, "staged_fallback_semantic": candidate}
    scheduler_receipt = {
        "initial_fetch_request_count": 8,
        "reserve_fetch_request_count": 2,
        "actual_fetch_request_count": 10,
        "initial_usable_page_count": 6,
        "reserve_usable_page_count": 2,
        "actual_usable_page_count": 8,
        "final_entities_with_two_or_more_usable_identity_sources": 2,
        "initial_usable_identity_source_count_vector": [1, 1, 2, 2],
        "final_usable_identity_source_count_vector": [2, 2, 2, 2],
        "reserve_target_entity_count": 2,
        "failed_url_retry_count": 0,
        "failed_url_retried": False,
        "same_model_query_and_total_fetch_target_caps_as_parent": True,
        "field_label_candidate_value_or_model_judgment_used_for_reserve_routing": False,
        "strict_two_independent_same_value_gate_changed": False,
        "query_text_used_to_establish_alignment": False,
    }
    semantic_receipt = {
        "final_changed_cell_count": 2,
        "projection_backed_eligible_support_set_count": 2,
        "new_model_search_fetch_or_evaluator_effect": 0,
        "candidate_changes_only_baseline_unknown_cells": True,
        "semantic_candidate_requires_projection_binding": True,
        "semantic_candidate_requires_two_independent_sources": True,
        "any_same_cell_value_conflict_abstains": True,
    }
    return {
        "opaque_id": task["opaque_id"],
        "predictions": predictions,
        "scheduler_receipt": scheduler_receipt,
        "semantic_receipt": semantic_receipt,
    }


def _parent(taxonomy: str = "success") -> dict:
    return {"failure_taxonomy": taxonomy}


class V24780StagedFallbackPackageTests(unittest.TestCase):
    def test_visible_parser_and_failure_projection_preserve_four_exact_rows(self) -> None:
        for task in contract.task_vector():
            entities = contract.visible_entities(task["question"])
            self.assertEqual(len(entities), 4)
            table = contract.failure_prediction(task)
            columns, rows = contract._baseline_matrix(table)
            self.assertEqual(columns, list(contract.EXPECTED_COLUMNS))
            self.assertEqual([row[0] for row in rows], entities)
            self.assertTrue(all(row[1:] == ["Unknown", "Unknown"] for row in rows))

    def test_parser_rejects_numbering_count_duplicates_and_pipe(self) -> None:
        question = contract.task_vector()[0]["question"]
        entities = contract.visible_entities(question)
        for altered in (
            question.replace("1. ", "2. ", 1),
            "\n".join(question.splitlines()[:-2] + question.splitlines()[-1:]),
            question.replace(f"2. {entities[1]}", f"2. {entities[0]}"),
            question.replace(entities[0], entities[0] + " | unsafe", 1),
        ):
            with self.assertRaises(ValueError):
                contract.visible_entities(altered)

    def test_failure_forward_row_requires_same_four_row_table_for_both_arms(self) -> None:
        task = contract.task_vector()[0]
        predictions = contract.failure_predictions(task)
        row = {
            "ordinal": 1,
            "opaque_id": task["opaque_id"],
            "predictions": predictions,
            "prediction_sha256": {
                arm: hashlib.sha256(value.encode()).hexdigest()
                for arm, value in predictions.items()
            },
            "runtime_result_valid": False,
        }
        self.assertEqual(contract.validate_forward_row(row), row)
        tampered = copy.deepcopy(row)
        tampered["predictions"]["staged_fallback_semantic"] = tampered["predictions"][
            "staged_fallback_semantic"
        ].replace("Unknown", "2001", 1)
        tampered["prediction_sha256"]["staged_fallback_semantic"] = hashlib.sha256(
            tampered["predictions"]["staged_fallback_semantic"].encode()
        ).hexdigest()
        with self.assertRaises(ValueError):
            contract.validate_forward_row(tampered)

    def test_success_observation_preserves_visible_identity_and_order(self) -> None:
        task = contract.task_vector()[0]
        result = _successful_result(task)
        with patch.object(contract, "validate_runtime_result", return_value=result):
            observation = contract.content_free_observation(result, task)
        self.assertEqual(observation["changed_cell_count"], 2)
        self.assertEqual(observation["founded_changed_cell_count"], 1)
        self.assertEqual(observation["country_changed_cell_count"], 1)
        self.assertEqual(observation["nonunknown_changed_cell_count"], 0)
        self.assertEqual(observation["initial_fetch_request_count"], 8)
        self.assertEqual(observation["reserve_fetch_request_count"], 2)
        self.assertEqual(observation["actual_fetch_request_count"], 10)
        self.assertEqual(
            observation["entity_slots_brought_to_two_sources_by_reserve"], 2
        )
        self.assertTrue(observation["scheduler_contract"])
        wrong = copy.deepcopy(result)
        wrong["predictions"]["baseline"] = wrong["predictions"]["baseline"].replace(
            contract.visible_entities(task["question"])[0], "Wrong Identity", 1
        )
        with patch.object(contract, "validate_runtime_result", return_value=wrong):
            with self.assertRaises(ValueError):
                contract.content_free_observation(wrong, task)

    def test_freeze_keeps_fixed_eight_task_denominator_on_all_failures(self) -> None:
        tasks = contract.task_vector()
        failure_types = (
            "child_nonzero_with_terminal_receipt",
            "hard_deadline_timeout",
            "result_envelope_invalid",
            "model_receipt_missing_or_invalid",
        )
        outcomes = [
            {
                "position": index,
                "task": task,
                "result": None,
                "observation": None,
                "valid": False,
                "parent_receipt": _parent(failure_types[(index - 1) % len(failure_types)]),
                "outcome_return_code": -15,
            }
            for index, task in enumerate(tasks, 1)
        ]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "PREDICTIONS", (base / "predictions.jsonl").relative_to(ROOT)),
                patch.object(runner, "RUN_SUMMARY", (base / "summary.json").relative_to(ROOT)),
                patch.object(runner, "PREDICTION_FREEZE", (base / "freeze.json").relative_to(ROOT)),
            ):
                frozen = runner._freeze(outcomes, 12.5)
        self.assertEqual(len(frozen["rows"]), 8)
        self.assertEqual(frozen["summary"]["valid_task_results"], 0)
        self.assertEqual(frozen["summary"]["projected_failure_tasks"], 8)
        self.assertEqual(frozen["summary"]["selected_arm_predictions"], 16)
        self.assertEqual(
            frozen["summary"]["parent_failure_taxonomy_counts"],
            {name: 2 for name in sorted(failure_types)},
        )
        self.assertTrue(
            all(row["predictions"]["baseline"] == row["predictions"]["staged_fallback_semantic"] for row in frozen["rows"])
        )

    def test_success_freeze_aggregates_staged_fetch_and_coverage_metrics(self) -> None:
        tasks = contract.task_vector()
        successful = _successful_result(tasks[0])
        with patch.object(
            contract, "validate_runtime_result", return_value=successful
        ):
            observation = contract.content_free_observation(successful, tasks[0])
        outcomes = [
            {
                "position": 1,
                "task": tasks[0],
                "result": successful,
                "observation": observation,
                "valid": True,
                "parent_receipt": _parent(),
                "outcome_return_code": 0,
            },
            *[
                {
                    "position": index,
                    "task": task,
                    "result": None,
                    "observation": None,
                    "valid": False,
                    "parent_receipt": _parent("result_envelope_invalid"),
                    "outcome_return_code": 1,
                }
                for index, task in enumerate(tasks[1:], 2)
            ],
        ]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "PREDICTIONS", (base / "predictions.jsonl").relative_to(ROOT)),
                patch.object(runner, "RUN_SUMMARY", (base / "summary.json").relative_to(ROOT)),
                patch.object(runner, "PREDICTION_FREEZE", (base / "freeze.json").relative_to(ROOT)),
            ):
                frozen = runner._freeze(outcomes, 12.5)
        summary = frozen["summary"]
        self.assertEqual(summary["initial_fetch_request_count"], 8)
        self.assertEqual(summary["reserve_fetch_request_count"], 2)
        self.assertEqual(summary["actual_fetch_request_count"], 10)
        self.assertEqual(summary["initial_usable_page_count"], 6)
        self.assertEqual(summary["reserve_usable_page_count"], 2)
        self.assertEqual(summary["actual_usable_page_count"], 8)
        self.assertEqual(summary["entity_slots_brought_to_two_sources_by_reserve"], 2)
        self.assertEqual(summary["final_entity_slots_with_two_usable_identity_sources"], 2)
        self.assertEqual(summary["failed_url_retry_count"], 0)
        self.assertEqual(summary["scheduler_contract_failed_task_count"], 0)
        for field, value in (
            ("actual_fetch_request_count", 81),
            ("failed_url_retry_count", 1),
        ):
            altered = copy.deepcopy(summary)
            altered[field] = value
            altered["summary_payload_sha256"] = contract.payload_sha256(
                {
                    key: current
                    for key, current in altered.items()
                    if key != "summary_payload_sha256"
                }
            )
            with self.assertRaises(ValueError):
                contract.validate_run_summary(altered)

    def test_total_wrapper_projects_child_parent_or_validation_exception_once(self) -> None:
        task = contract.task_vector()[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "OUTPUT_ROOT", base.relative_to(ROOT)),
                patch.object(runner, "TASK_ROOT", (base / "tasks").relative_to(ROOT)),
                patch.object(runner, "run_task", side_effect=ValueError("sensitive")) as called,
            ):
                item = runner.run_task_total(1, task)
            self.assertEqual(called.call_count, 1)
            self.assertFalse(item["valid"])
            self.assertEqual(
                item["parent_receipt"]["failure_taxonomy"],
                "parent_subprocess_exception",
            )

    def test_runner_uses_process_group_parent_and_exact_caps(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        child_source = Path(child.__file__).read_text(encoding="utf-8")
        self.assertIn("run_observed_subprocess(", source)
        self.assertIn("executor.submit(run_task_total", source)
        self.assertNotIn("executor.submit(run_task,", source)
        self.assertNotIn("expected_acquisitions=2", source)
        self.assertEqual(contract.PARENT_TIMEOUT_SECONDS, 195.0)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 8)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(
            [contract.LIMITS[key] for key in ("model_calls", "search_queries", "fetch_targets")],
            [2, 4, 10],
        )
        self.assertIn("HardTotalWallResponsesClient(", child_source)
        self.assertIn("DeadlineAwareGlobalModelSlotLimiter(", child_source)
        self.assertIn("HardTotalWallNativeSearchClient(", child_source)

        class Process:
            pid = 424242
            returncode = None
            waits = 0

            def wait(self, timeout):
                self.waits += 1
                if self.waits == 1:
                    raise subprocess.TimeoutExpired(["synthetic"], timeout)
                self.returncode = -signal.SIGTERM
                return self.returncode

        process = Process()
        launch: dict[str, object] = {}

        def popen(*_args, **kwargs):
            launch.update(kwargs)
            return process

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            with patch.object(observed.os, "killpg") as killed:
                outcome = observed.run_observed_subprocess(
                    cwd=ROOT,
                    output_root=ROOT / "outputs",
                    directory=Path(temporary),
                    command=["synthetic"],
                    environment={},
                    timeout_seconds=0.01,
                    result_validator=lambda _value: None,
                    model_receipt_validator=lambda _value: None,
                    transport_receipt_validator=lambda _value: None,
                    popen=popen,
                )
        self.assertTrue(outcome.timed_out)
        self.assertEqual(outcome.receipt["failure_taxonomy"], "hard_deadline_timeout")
        self.assertIs(launch["start_new_session"], True)
        killed.assert_called_once_with(process.pid, signal.SIGTERM)

    def test_single_visible_entity_scheduler_and_no_title_backfill(self) -> None:
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        self.assertEqual(
            source.count("scheduler = StagedFetchFallbackSearchClient("), 1
        )
        self.assertEqual(source.count("run_v24756_task("), 1)
        self.assertNotIn("ThinSameResponseCitationTitleBackfillSearchClient", source)
        child_source = Path(child.__file__).read_text(encoding="utf-8")
        self.assertNotIn("TaskUnionDiscoverySearchClient", child_source)
        self.assertNotIn("ThinSameResponseCitationTitleBackfillSearchClient", child_source)

    def test_child_main_path_constructs_clients_without_undefined_globals(self) -> None:
        task = contract.task_vector()[0]

        class Model:
            def __init__(self, *_args, **_kwargs):
                self.receipt_value = {"kind": "model"}

            def receipt(self):
                return self.receipt_value

        class Search:
            def __init__(self, *_args, **_kwargs):
                pass

            def transport_health(self):
                return {"kind": "transport"}

        class Limiter(Model):
            pass

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            task_dir = base / "task_0001"
            slots = base / "slots"
            task_dir.mkdir()
            slots.mkdir()
            task_path = task_dir / contract.VISIBLE_TASK_NAME
            task_path.write_text(json.dumps(task) + "\n", encoding="utf-8")
            args = [
                "run",
                "--task", str(task_path),
                "--result", str(task_dir / contract.RESULT_NAME),
                "--model-slot-directory", str(slots),
                "--model-receipt", str(task_dir / contract.MODEL_RECEIPT_NAME),
                "--transport-receipt", str(task_dir / contract.TRANSPORT_RECEIPT_NAME),
                "--terminal-receipt", str(task_dir / contract.TERMINAL_RECEIPT_NAME),
            ]
            with (
                patch.object(child, "OUTPUT_ROOT", base.relative_to(ROOT)),
                patch.object(child, "MODEL_SLOT_DIRECTORY", slots.relative_to(ROOT)),
                patch.object(child, "HardTotalWallResponsesClient", Model),
                patch.object(child, "DeadlineAwareGlobalModelSlotLimiter", Limiter),
                patch.object(child, "HardTotalWallNativeSearchClient", Search),
                patch.object(child, "run_v24778_task", return_value={"synthetic": True}),
                patch.object(sys, "argv", args),
            ):
                child.main()
            self.assertTrue((task_dir / contract.RESULT_NAME).is_file())
            self.assertTrue((task_dir / contract.TERMINAL_RECEIPT_NAME).is_file())

    def test_environment_is_minimal_and_carries_no_credentials(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "secret", "TAVILY_API_KEY": "secret"}):
            value = runner.environment()
        self.assertEqual(
            set(value),
            {"HOME", "USER", "LOGNAME", "PATH", "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE", "PYTHONSAFEPATH"},
        )
        self.assertNotIn("OPENAI_API_KEY", value)
        self.assertNotIn("TAVILY_API_KEY", value)


if __name__ == "__main__":
    unittest.main()
