from __future__ import annotations

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
from deepwide_agent import v24790_cross_tab_execution_contract as contract  # noqa: E402
from scripts import run_v24790_cross_tab_external as runner  # noqa: E402
from scripts import run_v24790_cross_tab_task as child  # noqa: E402


def parent(taxonomy: str = "success") -> dict:
    return {"failure_taxonomy": taxonomy}


def predictions(task: dict[str, str], *, changed: bool = False) -> dict[str, str]:
    entities = contract.visible_entities(task["question"])
    baseline = (
        "```markdown\n| Organization | Founded | Country |\n| --- | --- | --- |\n"
        + "\n".join(f"| {entity} | Unknown | Unknown |" for entity in entities)
        + "\n```"
    )
    candidate = (
        "```markdown\n| Organization | Founded | Country |\n| --- | --- | --- |\n"
        + "\n".join(
            f"| {entity} | {'2001' if changed and index == 0 else 'Unknown'} | Unknown |"
            for index, entity in enumerate(entities)
        )
        + "\n```"
    )
    return {"baseline": baseline, "staged_fallback_semantic": candidate}


def selected_counts(*, multi=False, support=False, proposal=False, changed=False, strict=False) -> dict[str, int]:
    value = {name: 0 for name in contract.SELECTED_SUM_FIELDS}
    value.update(
        target_count=1,
        unknown_target_count=1,
        projection_group_count=1,
        unknown_projection_group_count=1,
        unknown_single_source_projection_group_count=int(not multi),
        unknown_two_or_more_source_projection_group_count=int(multi),
        catalog_candidate_group_count=1,
        catalog_eligible_support_set_count=int(support),
        projection_backed_support_group_count=int(support),
        unconflicted_unknown_proposal_group_count=int(proposal),
        changed_target_count=int(changed),
        changed_to_projected_value_group_count=int(strict),
        strict_joint_safe_change_group_count=int(strict),
    )
    return value


def observation(
    status: str, *, multi=False, support=False, proposal=False,
    changed=False, strict=False,
) -> dict:
    base_valid = status in {
        "validated", "no_baseline_unknown_target", "private_catalog_absent",
        "selected_catalog_or_observer_failure",
    }
    receipt_valid = status == "validated"
    local = {
        "has_unknown_projection_group": True,
        "has_unknown_two_or_more_source_projection_group": multi,
        "has_projection_backed_support_group": support,
        "has_unconflicted_unknown_proposal_group": proposal,
        "has_changed_target": changed,
        "has_strict_joint_safe_change_group": strict,
    } if receipt_valid else None
    return {
        "status": status,
        "base_result_valid": base_valid,
        "selected_receipt_valid": receipt_valid,
        "prediction_changed": changed and base_valid,
        "changed_cell_count": int(changed and base_valid),
        "nonunknown_changed_cell_count": 0,
        "selected_counts": selected_counts(
            multi=multi, support=support, proposal=proposal,
            changed=changed, strict=strict,
        ) if receipt_valid else None,
        "selected_task_local": local,
        "selected_receipt_contract": receipt_valid,
        "initial_fetch_request_count": 8 if base_valid else 0,
        "reserve_fetch_request_count": 2 if base_valid else 0,
        "actual_fetch_request_count": 10 if base_valid else 0,
        "initial_usable_page_count": 6 if base_valid else 0,
        "reserve_usable_page_count": 2 if base_valid else 0,
        "actual_usable_page_count": 8 if base_valid else 0,
        "failed_url_retry_count": 0,
        "scheduler_contract": base_valid,
        "semantic_safety_contract": base_valid,
    }


def result(task: dict[str, str], status: str, *, changed=False) -> dict:
    base_valid = status in {
        "validated", "no_baseline_unknown_target", "private_catalog_absent",
        "selected_catalog_or_observer_failure",
    }
    return {
        "status": status,
        "base_result_valid": base_valid,
        "selected_receipt_valid": status == "validated",
        "predictions": predictions(task, changed=changed) if base_valid else {},
    }


class V24790CrossTabPackageTests(unittest.TestCase):
    def freeze(self, outcomes: list[dict], wall: float = 12.5) -> dict:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "PREDICTIONS", (base / "predictions.jsonl").relative_to(ROOT)),
                patch.object(runner, "RUN_SUMMARY", (base / "summary.json").relative_to(ROOT)),
                patch.object(runner, "PREDICTION_FREEZE", (base / "freeze.json").relative_to(ROOT)),
            ):
                return runner._freeze(outcomes, wall)

    def test_all_parent_failures_keep_fixed_denominator(self) -> None:
        tasks = contract.task_vector()
        outcomes = [{
            "position": index, "task": task, "result": None, "observation": None,
            "projection_valid": False, "parent_receipt": parent("hard_deadline_timeout"),
            "outcome_return_code": -15,
        } for index, task in enumerate(tasks, 1)]
        frozen = self.freeze(outcomes)
        self.assertEqual(len(frozen["rows"]), 8)
        self.assertEqual(frozen["summary"]["status_parent_failure_count"], 8)
        self.assertEqual(frozen["summary"]["selected_receipt_valid_task_count"], 0)
        self.assertEqual(frozen["summary"]["target_count"], 0)
        self.assertTrue(frozen["summary"]["missing_selected_receipts_not_aggregated_as_zero"])

    def test_mixed_missing_receipts_are_not_aggregated_as_zero(self) -> None:
        tasks = contract.task_vector()
        statuses = (
            "validated", "no_baseline_unknown_target", "private_catalog_absent",
            "base_runtime_failure", "parent_failure", "validated",
            "selected_catalog_or_observer_failure", "private_catalog_absent",
        )
        outcomes = []
        for index, (task, status) in enumerate(zip(tasks, statuses, strict=True), 1):
            projection_valid = status != "parent_failure"
            current = result(task, status) if projection_valid else None
            current_observation = observation(status) if projection_valid else None
            outcomes.append({
                "position": index, "task": task, "result": current,
                "observation": current_observation, "projection_valid": projection_valid,
                "parent_receipt": parent("success" if projection_valid else "result_envelope_invalid"),
                "outcome_return_code": 0 if projection_valid else 1,
            })
        summary = self.freeze(outcomes)["summary"]
        self.assertEqual(summary["selected_receipt_valid_task_count"], 2)
        self.assertEqual(summary["target_count"], 2)
        self.assertEqual(summary["unknown_target_count"], 2)
        self.assertEqual(summary["status_parent_failure_count"], 1)

    def test_cross_task_margins_do_not_create_strict_joint(self) -> None:
        tasks = contract.task_vector()
        properties = [
            dict(multi=True),
            dict(support=True, proposal=True, changed=True),
            {}, {}, {}, {}, {}, {},
        ]
        outcomes = []
        for index, (task, flags) in enumerate(zip(tasks, properties, strict=True), 1):
            outcomes.append({
                "position": index, "task": task,
                "result": result(task, "validated", changed=bool(flags.get("changed"))),
                "observation": observation("validated", **flags),
                "projection_valid": True, "parent_receipt": parent(),
                "outcome_return_code": 0,
            })
        summary = self.freeze(outcomes)["summary"]
        self.assertEqual(summary["has_unknown_two_or_more_source_projection_group_task_count"], 1)
        self.assertEqual(summary["has_changed_target_task_count"], 1)
        self.assertEqual(summary["has_strict_joint_safe_change_group_task_count"], 0)
        self.assertEqual(summary["strict_joint_safe_change_group_count"], 0)
        self.assertFalse(summary["cross_task_or_cross_group_margins_used_as_joint"])

    def test_total_wrapper_never_retries_parent_exception(self) -> None:
        task = contract.task_vector()[0]
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            with (
                patch.object(runner, "OUTPUT_ROOT", base.relative_to(ROOT)),
                patch.object(runner, "TASK_ROOT", (base / "tasks").relative_to(ROOT)),
                patch.object(runner, "run_task", side_effect=ValueError("sensitive")) as called,
            ):
                value = runner.run_task_total(1, task)
        self.assertEqual(called.call_count, 1)
        self.assertFalse(value["projection_valid"])
        self.assertEqual(value["parent_receipt"]["failure_taxonomy"], "parent_subprocess_exception")

    def test_child_constructs_clients_and_calls_v24790_once(self) -> None:
        task = contract.task_vector()[0]

        class Model:
            def __init__(self, *_args, **_kwargs): pass
            def receipt(self): return {"kind": "model"}

        class Search:
            def __init__(self, *_args, **_kwargs): pass
            def transport_health(self): return {"kind": "transport"}

        class Limiter(Model): pass

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            task_dir = base / "task_0001"
            slots = base / "slots"
            task_dir.mkdir(); slots.mkdir()
            task_path = task_dir / contract.VISIBLE_TASK_NAME
            task_path.write_text(json.dumps(task) + "\n", encoding="utf-8")
            args = [
                "run", "--task", str(task_path),
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
                patch.object(child, "run_v24790_task", return_value={"synthetic": True}) as called,
                patch.object(sys, "argv", args),
            ):
                child.main()
            self.assertEqual(called.call_count, 1)
            self.assertTrue((task_dir / contract.RESULT_NAME).is_file())
            self.assertTrue((task_dir / contract.TERMINAL_RECEIPT_NAME).is_file())

    def test_runner_uses_process_group_and_exact_caps(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn("run_observed_subprocess(", source)
        self.assertIn("executor.submit(run_task_total", source)
        self.assertNotIn("executor.submit(run_task,", source)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 8)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)

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

        process = Process(); launch: dict[str, object] = {}
        def popen(*_args, **kwargs): launch.update(kwargs); return process
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            with patch.object(observed.os, "killpg") as killed:
                outcome = observed.run_observed_subprocess(
                    cwd=ROOT, output_root=ROOT / "outputs", directory=Path(temporary),
                    command=["synthetic"], environment={}, timeout_seconds=0.01,
                    result_validator=lambda _value: None,
                    model_receipt_validator=lambda _value: None,
                    transport_receipt_validator=lambda _value: None,
                    popen=popen,
                )
        self.assertTrue(outcome.timed_out)
        self.assertIs(launch["start_new_session"], True)
        killed.assert_called_once_with(process.pid, signal.SIGTERM)

    def test_environment_and_forward_sources_are_label_blind(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "secret", "TAVILY_API_KEY": "secret"}):
            value = runner.environment()
        self.assertNotIn("OPENAI_API_KEY", value)
        self.assertNotIn("TAVILY_API_KEY", value)
        for path in (Path(contract.__file__), Path(child.__file__), Path(runner.__file__)):
            source = path.read_text(encoding="utf-8")
            for marker in ("evaluation/", "population_private", "private_truth.json", "evaluator_mapping"):
                self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
