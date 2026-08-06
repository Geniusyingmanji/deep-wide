from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import DeadlineAwareNativeSearchClient  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24671_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24671_task,
    validate_envelope,
)
from scripts import run_v24671_information_gain as runner  # noqa: E402
from test_v24655_unknown_cell_targeted_runtime import (  # noqa: E402
    Model,
    Search,
    TASK,
    limits,
)


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class DeadlineSearch(DeadlineAwareNativeSearchClient, Search):
    def __init__(self, clock):
        DeadlineAwareNativeSearchClient.__init__(
            self,
            "http://unused.invalid/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=400,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        Search.__init__(self)


def slots(root: Path):
    value = root / "slots"
    value.mkdir()
    for index in range(1, 9):
        (value / f"slot_{index:02d}.lock").write_text("{}\n")
    return value


class V24671ForwardPackageTests(unittest.TestCase):
    def test_runner_requires_control_artifacts_before_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(runner, "ROOT", root), patch.object(
                runner.subprocess, "Popen"
            ) as process, patch.object(
                runner, "acquire_deepwide_api_lease"
            ) as lease:
                with self.assertRaises(RuntimeError):
                    runner.main()
            process.assert_not_called()
            lease.assert_not_called()

    def test_integrated_envelope_is_information_gain_strict_and_label_blind(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model = build_deadline_model(
                url="http://unused.invalid/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=180,
                max_retries=2,
                slot_directory=slots(output),
                output_root=output,
                slot_cap=8,
                pool_id=POOL_ID,
                absolute_deadline=400,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                monotonic=clock,
                sleeper=clock.sleep,
                inner=Model(),
            )
            search = DeadlineSearch(clock)
            outcome = run_v24671_task(
                TASK, model=model, search=search, limits=limits(), monotonic=clock
            )
            envelope = validate_envelope(build_envelope(outcome))
            receipt = envelope["result"]["receipt"]
            self.assertEqual(receipt["selected_unknown_target_cap"], 1)
            self.assertEqual(receipt["concentrated_targeted_fetch_cap"], 4)
            self.assertFalse(receipt["support_threshold_relaxed"])
            self.assertFalse(receipt["positive_decision_credit_assigned"])
            self.assertFalse(
                envelope[
                    "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
                ]
            )

    def test_envelope_reseal_cannot_authorize_evaluator(self):
        source = (
            ROOT / "src/deepwide_agent/v24671_runner_integration.py"
        ).read_text()
        self.assertIn("benchmark_launch_or_evaluator_authorized", source)
        self.assertIn("is not False", source)

    def test_failure_projection_is_identical_for_both_arms(self):
        prediction = runner.fallback(runner.task_vector()[0])
        self.assertEqual(set(prediction), set(runner.ARMS))
        self.assertEqual(len(set(prediction.values())), 1)

    def test_no_resume_retry_or_skip_entrypoint(self):
        tree = ast.parse(
            (ROOT / "scripts/run_v24671_information_gain.py").read_text()
        )
        functions = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertFalse(
            functions & {"resume", "retry", "rerun", "skip", "run_missing"}
        )

    def test_forward_files_have_no_evaluator_surface(self):
        for relative in (
            "src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py",
            "src/deepwide_agent/v24671_runner_integration.py",
            "scripts/run_v24671_ror_task.py",
            "scripts/run_v24671_information_gain.py",
            "scripts/audit_v24671_forward.py",
        ):
            source = (ROOT / relative).read_text()
            self.assertNotIn("evaluation/", source)
            self.assertNotIn("external_evaluator", source)
            self.assertNotIn("ror_gold", source)


if __name__ == "__main__":
    unittest.main()
