from __future__ import annotations

import copy
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

from deepwide_agent import v24309_runner_exit_integration as observed  # noqa: E402
from deepwide_agent import v24784_projection_funnel_execution_contract as contract  # noqa: E402
from scripts import run_v24784_projection_funnel_external as runner  # noqa: E402
from scripts import run_v24784_projection_funnel_task as child  # noqa: E402


def parent(taxonomy: str = "success") -> dict:
    return {"failure_taxonomy": taxonomy}


def predictions(task: dict[str, str], *, changed: bool = False) -> dict[str, str]:
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
            f"| {entity} | {'2001' if changed and index == 0 else 'Unknown'} | Unknown |"
            for index, entity in enumerate(entities)
        )
        + "\n```"
    )
    return {"baseline": baseline, "staged_fallback_semantic": candidate}


def funnel_counts() -> dict[str, int]:
    value = {name: 0 for name in contract.FUNNEL_SUM_FIELDS}
    value.update(
        target_count=8,
        baseline_unknown_target_count=8,
        core_page_count=6,
        reserve_page_count=2,
        input_page_count=8,
        intact_page_count=8,
        page_target_pair_count=64,
        supported_column_pair_count=64,
        exact_entity_anchor_pair_count=2,
        target_segment_pair_count=2,
        explicit_relation_token_pair_count=2,
        parsable_relation_pair_count=2,
        bound_relation_pair_count=2,
        projection_emitted_pair_count=2,
        semantic_projection_count=2,
        distinct_target_value_projection_count=1,
        projection_target_binding_count=1,
        projection_unknown_target_value_group_count=1,
        projection_two_or_more_source_group_count=1,
        catalog_candidate_target_value_group_count=1,
        catalog_eligible_support_set_count=1,
        projection_backed_eligible_support_set_count=1,
        unconflicted_projection_backed_unknown_proposal_count=1,
    )
    return value


def observation(status: str, *, changed: bool = False) -> dict:
    base_valid = status in {
        "validated",
        "private_catalog_absent",
        "funnel_validation_failure",
    }
    funnel_valid = status == "validated"
    return {
        "status": status,
        "base_result_valid": base_valid,
        "funnel_receipt_valid": funnel_valid,
        "prediction_changed": changed and base_valid,
        "changed_cell_count": int(changed and base_valid),
        "founded_changed_cell_count": int(changed and base_valid),
        "country_changed_cell_count": 0,
        "nonunknown_changed_cell_count": 0,
        "projection_backed_support_set_count": int(changed and base_valid),
        "initial_fetch_request_count": 8 if base_valid else 0,
        "reserve_fetch_request_count": 2 if base_valid else 0,
        "actual_fetch_request_count": 10 if base_valid else 0,
        "initial_usable_page_count": 6 if base_valid else 0,
        "reserve_usable_page_count": 2 if base_valid else 0,
        "actual_usable_page_count": 8 if base_valid else 0,
        "final_entity_slots_with_two_usable_identity_sources": 2 if base_valid else 0,
        "entity_slots_brought_to_two_sources_by_reserve": 2 if base_valid else 0,
        "reserve_target_entity_count": 2 if base_valid else 0,
        "failed_url_retry_count": 0,
        "scheduler_contract": base_valid,
        "candidate_changes_only_unknown": base_valid,
        "semantic_safety_contract": base_valid,
        "funnel_counts": funnel_counts() if funnel_valid else None,
        "task_local_joint_projection_backed_safe_change": changed and funnel_valid,
    }


def result(task: dict[str, str], status: str, *, changed: bool = False) -> dict:
    base_valid = status in {
        "validated",
        "private_catalog_absent",
        "funnel_validation_failure",
    }
    funnel_valid = status == "validated"
    return {
        "status": status,
        "base_result_valid": base_valid,
        "funnel_receipt_valid": funnel_valid,
        "predictions": predictions(task, changed=changed) if base_valid else {},
        "projection_funnel_receipt": (
            {
                **funnel_counts(),
                "reason_counts": {
                    name: (64 if name == "explicit_relation_absent" else 0)
                    for name in contract.funnel.REASONS
                },
            }
            if funnel_valid
            else None
        ),
    }


class V24784ProjectionFunnelPackageTests(unittest.TestCase):
    def freeze(self, outcomes: list[dict], wall: float = 12.5) -> dict:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(
                    runner,
                    "PREDICTIONS",
                    (base / "predictions.jsonl").relative_to(ROOT),
                ),
                patch.object(
                    runner,
                    "RUN_SUMMARY",
                    (base / "summary.json").relative_to(ROOT),
                ),
                patch.object(
                    runner,
                    "PREDICTION_FREEZE",
                    (base / "freeze.json").relative_to(ROOT),
                ),
            ):
                return runner._freeze(outcomes, wall)

    def test_all_parent_failures_keep_fixed_denominator_and_explicit_status(self) -> None:
        tasks = contract.task_vector()
        outcomes = [
            {
                "position": index,
                "task": task,
                "result": None,
                "observation": None,
                "projection_valid": False,
                "parent_receipt": parent("hard_deadline_timeout"),
                "outcome_return_code": -15,
            }
            for index, task in enumerate(tasks, 1)
        ]
        frozen = self.freeze(outcomes)
        summary = frozen["summary"]
        self.assertEqual(len(frozen["rows"]), 8)
        self.assertEqual(summary["status_parent_failure_count"], 8)
        self.assertEqual(summary["projected_failure_tasks"], 8)
        self.assertEqual(summary["validated_funnel_task_count"], 0)
        self.assertEqual(summary["page_target_pair_count"], 0)
        self.assertTrue(
            all(
                row["predictions"]["baseline"]
                == row["predictions"]["staged_fallback_semantic"]
                for row in frozen["rows"]
            )
        )

    def test_mixed_statuses_do_not_turn_missing_funnels_into_zero_observations(self) -> None:
        tasks = contract.task_vector()
        statuses = (
            "validated",
            "private_catalog_absent",
            "funnel_validation_failure",
            "base_runtime_failure",
            "parent_failure",
            "validated",
            "private_catalog_absent",
            "funnel_validation_failure",
        )
        outcomes = []
        for index, (task, status) in enumerate(zip(tasks, statuses, strict=True), 1):
            projection_valid = status != "parent_failure"
            current = result(task, status, changed=status == "validated") if projection_valid else None
            current_observation = (
                observation(status, changed=status == "validated")
                if projection_valid
                else None
            )
            outcomes.append(
                {
                    "position": index,
                    "task": task,
                    "result": current,
                    "observation": current_observation,
                    "projection_valid": projection_valid,
                    "parent_receipt": parent("success" if projection_valid else "result_envelope_invalid"),
                    "outcome_return_code": 0 if projection_valid else 1,
                }
            )
        frozen = self.freeze(outcomes)
        summary = frozen["summary"]
        self.assertEqual(summary["status_validated_count"], 2)
        self.assertEqual(summary["status_private_catalog_absent_count"], 2)
        self.assertEqual(summary["status_funnel_validation_failure_count"], 2)
        self.assertEqual(summary["status_base_runtime_failure_count"], 1)
        self.assertEqual(summary["status_parent_failure_count"], 1)
        self.assertEqual(summary["validated_funnel_task_count"], 2)
        self.assertEqual(summary["target_count"], 16)
        self.assertEqual(summary["page_target_pair_count"], 128)
        self.assertEqual(
            summary["funnel_reason_counts"]["explicit_relation_absent"], 128
        )
        self.assertEqual(summary["task_local_joint_projection_backed_safe_change_task_count"], 2)

    def test_total_wrapper_never_retries_parent_exception(self) -> None:
        task = contract.task_vector()[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "OUTPUT_ROOT", base.relative_to(ROOT)),
                patch.object(
                    runner, "TASK_ROOT", (base / "tasks").relative_to(ROOT)
                ),
                patch.object(
                    runner, "run_task", side_effect=ValueError("sensitive")
                ) as called,
            ):
                value = runner.run_task_total(1, task)
        self.assertEqual(called.call_count, 1)
        self.assertFalse(value["projection_valid"])
        self.assertEqual(
            value["parent_receipt"]["failure_taxonomy"],
            "parent_subprocess_exception",
        )

    def test_child_main_constructs_clients_without_undefined_globals(self) -> None:
        task = contract.task_vector()[0]

        class Model:
            def __init__(self, *_args, **_kwargs):
                pass

            def receipt(self):
                return {"kind": "model"}

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
                "--task",
                str(task_path),
                "--result",
                str(task_dir / contract.RESULT_NAME),
                "--model-slot-directory",
                str(slots),
                "--model-receipt",
                str(task_dir / contract.MODEL_RECEIPT_NAME),
                "--transport-receipt",
                str(task_dir / contract.TRANSPORT_RECEIPT_NAME),
                "--terminal-receipt",
                str(task_dir / contract.TERMINAL_RECEIPT_NAME),
            ]
            with (
                patch.object(child, "OUTPUT_ROOT", base.relative_to(ROOT)),
                patch.object(
                    child, "MODEL_SLOT_DIRECTORY", slots.relative_to(ROOT)
                ),
                patch.object(child, "HardTotalWallResponsesClient", Model),
                patch.object(
                    child, "DeadlineAwareGlobalModelSlotLimiter", Limiter
                ),
                patch.object(child, "HardTotalWallNativeSearchClient", Search),
                patch.object(
                    child, "run_v24784_task", return_value={"synthetic": True}
                ) as called,
                patch.object(sys, "argv", args),
            ):
                child.main()
            self.assertEqual(called.call_count, 1)
            self.assertTrue((task_dir / contract.RESULT_NAME).is_file())
            self.assertTrue((task_dir / contract.TERMINAL_RECEIPT_NAME).is_file())

    def test_runner_uses_process_group_and_exact_caps(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        child_source = Path(child.__file__).read_text(encoding="utf-8")
        self.assertIn("run_observed_subprocess(", source)
        self.assertIn("executor.submit(run_task_total", source)
        self.assertNotIn("executor.submit(run_task,", source)
        self.assertEqual(contract.PARENT_TIMEOUT_SECONDS, 195.0)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 8)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
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
        self.assertIs(launch["start_new_session"], True)
        killed.assert_called_once_with(process.pid, signal.SIGTERM)

    def test_environment_is_minimal_and_has_no_credentials(self) -> None:
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "secret", "TAVILY_API_KEY": "secret"},
        ):
            value = runner.environment()
        self.assertEqual(
            set(value),
            {
                "HOME",
                "USER",
                "LOGNAME",
                "PATH",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONNOUSERSITE",
                "PYTHONSAFEPATH",
            },
        )
        self.assertNotIn("OPENAI_API_KEY", value)
        self.assertNotIn("TAVILY_API_KEY", value)

    def test_forward_sources_have_no_private_population_or_old_output_marker(self) -> None:
        for path in (Path(contract.__file__), Path(child.__file__), Path(runner.__file__)):
            source = path.read_text(encoding="utf-8")
            for marker in (
                "evaluation/",
                "population_private",
                "outputs/v24780_staged_fallback_external_v1",
                "evaluator_mapping",
            ):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
