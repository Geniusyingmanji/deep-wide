from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24267_total_fallback as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    validate_v24259_result,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    validate_receipt,
)
from scripts.preregister_v24266_exact220 import (  # noqa: E402
    build_protocol,
    selected_tasks,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "Return a table. Column names: Name, Value.",
}
PIPE_TASK = {
    "opaque_id": "task_89abcdef0123456701234567",
    "question": "Return a table. Column names: Name | Value | Example.",
}


class Counters:
    def __init__(self) -> None:
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 7
        self.output_tokens += 3
        self.total_tokens += 10
        return SimpleNamespace(text="unused")


class Search:
    def __init__(self) -> None:
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0


def prepare_slots(root: Path) -> Path:
    slots = root / "slots"
    slots.mkdir()
    for index in range(1, 3):
        (slots / f"slot_{index:02d}.lock").write_text("slot\n", encoding="utf-8")
    return slots


class V24267TotalFallbackTests(unittest.TestCase):
    def test_pipe_header_fallback_is_always_canonical_and_content_free(self) -> None:
        value = target.build_total_fallback_result(
            PIPE_TASK,
            limits=ScoreFirstLimits(),
            completion_kind="worker_failure_fallback",
            failure_stage="synthetic",
            failure_type="SyntheticFailure",
            elapsed_seconds=0.1,
        )
        validate_v24259_result(value)
        self.assertEqual(value["columns"], ["Result"])
        self.assertEqual(
            value["prediction"],
            "```markdown\n| Result |\n| --- |\n| Unknown |\n```",
        )
        self.assertNotIn("Name | Value", json.dumps(value, ensure_ascii=False))

    def test_hostile_progress_values_cannot_break_total_fallback(self) -> None:
        value = target.build_total_fallback_result(
            PIPE_TASK,
            limits=ScoreFirstLimits(),
            completion_kind="worker_failure_fallback",
            failure_stage="synthetic",
            failure_type="SyntheticFailure",
            elapsed_seconds=float("nan"),
            last_progress={
                "admitted_model_calls": object(),
                "admitted_search_queries": -10,
                "admitted_fetch_targets": 10**9,
                "events": [{"stage": object()}],
                "model_cost": {"requests": "bad"},
                "search_cost": None,
            },
        )
        validate_v24259_result(value)
        self.assertEqual(value["budget"]["elapsed_seconds"], 0.0)
        self.assertEqual(value["budget"]["admitted_fetch_targets"], 24)
        self.assertEqual(value["cost"]["model"]["requests"], 0)

    def test_final_parent_validator_exception_becomes_terminal_fallback(self) -> None:
        invalid = target.build_total_fallback_result(
            TASK,
            limits=ScoreFirstLimits(),
            completion_kind="worker_failure_fallback",
            failure_stage="seed",
            failure_type="Seed",
            elapsed_seconds=0.0,
        )
        invalid["prediction"] += "\n"
        with mock.patch.object(target, "run_v24259_task", return_value=invalid):
            value = target.run_total_task(
                TASK, model=Counters(), search=Search(), limits=ScoreFirstLimits()
            )
        validate_v24259_result(value)
        self.assertEqual(value["completion_kind"], "worker_failure_fallback")
        self.assertEqual(value["failures"][0]["type"], "ValueError")

    def test_privileged_metadata_is_rejected_before_any_effect(self) -> None:
        model = Counters()
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            target.run_total_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_actual_model_counters_match_global_slot_receipt_after_exception(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            inner = Counters()
            model = GlobalModelSlotLimiter(
                inner,
                slot_directory=prepare_slots(output_root),
                output_root=output_root,
            )
            search = Search()

            def fail_after_one_effect(_task, **kwargs):
                kwargs["model"].complete("system", "user", max_output_tokens=1)
                kwargs["progress"](
                    {
                        "admitted_model_calls": 1,
                        "admitted_search_queries": 0,
                        "admitted_fetch_targets": 0,
                    }
                )
                raise ValueError("private exception detail")

            with mock.patch.object(
                target, "run_v24259_task", side_effect=fail_after_one_effect
            ):
                value = target.run_total_task(
                    TASK, model=model, search=search, limits=ScoreFirstLimits()
                )
            validate_v24259_result(value)
            receipt = model.receipt()
            validate_receipt(
                receipt,
                expected_acquisitions=value["cost"]["model"]["requests"],
            )
        self.assertEqual(value["cost"]["model"]["requests"], 1)
        self.assertNotIn("private exception detail", json.dumps(value))

    def test_all_frozen_visible_220_tasks_have_a_canonical_total_fallback(self) -> None:
        protocol = build_protocol(ROOT, now=1, require_pristine=False)
        tasks = selected_tasks(ROOT, protocol)
        limits = ScoreFirstLimits(**dict(protocol["limits"]))
        self.assertEqual(len(tasks), 220)
        for task in tasks:
            value = target.build_total_fallback_result(
                task,
                limits=limits,
                completion_kind="worker_failure_fallback",
                failure_stage="preflight_totality",
                failure_type="SyntheticFailure",
                elapsed_seconds=0.0,
            )
            validate_v24259_result(value)
            self.assertEqual(value["opaque_id"], task["opaque_id"])
            self.assertNotIn(task["question"], json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
