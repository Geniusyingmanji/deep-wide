from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    parent_receipt,
)
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_directory_observation,
    run_and_persist_uncertainty_task,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24391_uncertainty_active_evidence_runner import clients  # noqa: E402


def writer(directory: Path):
    def write(name: str, value) -> None:
        path = directory / name
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")

    return write


def terminal(*, success: bool, model: bool, transport: bool) -> dict:
    return child_receipt(
        stage="result_envelope_written" if success else "child_exception",
        exception_type=None if success else "RuntimeError",
        model_receipt_written=model,
        transport_receipt_written=transport,
        result_envelope_written=success,
    )


def parent(*, success: bool, model: bool, transport: bool) -> dict:
    return parent_receipt(
        return_code=0 if success else 1,
        timed_out=False,
        elapsed_seconds=4.0,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=success,
        result_envelope_valid=success,
        model_receipt_present=model,
        model_receipt_valid=model,
        transport_receipt_present=transport,
        transport_receipt_valid=transport,
    )


class V24399FailureObservableRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def test_success_path_persists_four_independent_artifacts(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock, deadline=300)
        outcome = run_and_persist_uncertainty_task(
            TASK,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(directory),
        )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            self.assertTrue((directory / name).is_file())
        self.assertFalse((directory / FAILURE_NAME).exists())
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal(success=True, model=True, transport=True)),
            encoding="utf-8",
        )
        observation = build_directory_observation(
            1,
            parent(success=True, model=True, transport=True),
            directory=directory,
            expected_model_cap=2,
        )
        self.assertEqual(observation["parent_taxonomy"], "success")
        self.assertEqual(
            observation["model_acquisitions"],
            outcome.model_slot_receipt["acquisitions"],
        )
        self.assertEqual(
            observation["effect_scope"], "successful_terminal_receipts"
        )

    def test_runtime_failure_persists_partial_receipts_before_reraise(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock, deadline=300)
        with patch(
            "deepwide_agent.v24399_failure_observable_runner.run_v24391_task",
            side_effect=RuntimeError("private runtime detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_uncertainty_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(directory),
                )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, FAILURE_NAME):
            self.assertTrue((directory / name).is_file())
        self.assertFalse((directory / RESULT_NAME).exists())
        self.assertNotIn(
            "private runtime detail",
            (directory / FAILURE_NAME).read_text(encoding="utf-8"),
        )
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal(success=False, model=True, transport=True)),
            encoding="utf-8",
        )
        observation = build_directory_observation(
            1,
            parent(success=False, model=True, transport=True),
            directory=directory,
            expected_model_cap=2,
        )
        self.assertEqual(
            observation["parent_taxonomy"],
            "child_nonzero_with_terminal_receipt",
        )
        self.assertEqual(observation["failure_stage"], "runtime")
        self.assertEqual(observation["failure_exception_type"], "RuntimeError")
        self.assertEqual(observation["effect_scope"], "failure_partial_receipts")

    def test_model_construction_failure_preserves_unobserved_scope(self) -> None:
        directory = self.make_directory()

        def fail_model():
            raise RuntimeError("private construction detail")

        with self.assertRaises(RuntimeError):
            run_and_persist_uncertainty_task(
                TASK,
                model_factory=fail_model,
                search_factory=lambda: None,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=Clock(),
                expected_model_cap=2,
                writer=writer(directory),
            )
        self.assertTrue((directory / FAILURE_NAME).is_file())
        self.assertFalse((directory / MODEL_NAME).exists())
        self.assertFalse((directory / TRANSPORT_NAME).exists())
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal(success=False, model=False, transport=False)),
            encoding="utf-8",
        )
        observation = build_directory_observation(
            1,
            parent(success=False, model=False, transport=False),
            directory=directory,
            expected_model_cap=2,
        )
        self.assertEqual(observation["failure_stage"], "model_construction")
        self.assertEqual(observation["effect_scope"], "unobserved_lower_bound")

    def test_search_construction_failure_preserves_model_lower_bound(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, _ = clients(directory, clock, deadline=300)

        def fail_search():
            raise RuntimeError("private search construction detail")

        with self.assertRaises(RuntimeError):
            run_and_persist_uncertainty_task(
                TASK,
                model_factory=lambda: model,
                search_factory=fail_search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                writer=writer(directory),
            )
        self.assertTrue((directory / MODEL_NAME).is_file())
        self.assertTrue((directory / FAILURE_NAME).is_file())
        self.assertFalse((directory / TRANSPORT_NAME).exists())
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal(success=False, model=True, transport=False)),
            encoding="utf-8",
        )
        observation = build_directory_observation(
            1,
            parent(success=False, model=True, transport=False),
            directory=directory,
            expected_model_cap=2,
        )
        self.assertEqual(observation["failure_stage"], "search_construction")
        self.assertTrue(observation["model_effects_observed"])
        self.assertFalse(observation["transport_effects_observed"])
        self.assertEqual(observation["effect_scope"], "unobserved_lower_bound")

    def test_parent_hard_timeout_needs_no_private_artifact(self) -> None:
        directory = self.make_directory()
        timeout_parent = parent_receipt(
            return_code=-15,
            timed_out=True,
            elapsed_seconds=230.0,
            subprocess_exception=False,
            child_terminal_receipt_present=False,
            child_terminal_receipt_valid=False,
            result_envelope_present=False,
            result_envelope_valid=False,
            model_receipt_present=False,
            model_receipt_valid=False,
            transport_receipt_present=False,
            transport_receipt_valid=False,
        )
        observation = build_directory_observation(
            1,
            timeout_parent,
            directory=directory,
            expected_model_cap=2,
        )
        self.assertEqual(observation["parent_taxonomy"], "hard_deadline_timeout")
        self.assertEqual(observation["deadline_evidence"], "parent_hard_timeout")

    def test_failure_snapshot_receipt_hash_tamper_is_rejected(self) -> None:
        directory = self.make_directory()
        clock = Clock()
        model, search = clients(directory, clock, deadline=300)
        with patch(
            "deepwide_agent.v24399_failure_observable_runner.run_v24391_task",
            side_effect=RuntimeError("ignored"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_uncertainty_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(directory),
                )
        model_value = json.loads((directory / MODEL_NAME).read_text(encoding="utf-8"))
        model_value["total_wait_seconds"] += 1.0
        (directory / MODEL_NAME).write_text(
            json.dumps(model_value), encoding="utf-8"
        )
        (directory / "child_terminal_receipt.json").write_text(
            json.dumps(terminal(success=False, model=True, transport=True)),
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            build_directory_observation(
                1,
                parent(success=False, model=True, transport=True),
                directory=directory,
                expected_model_cap=2,
            )


if __name__ == "__main__":
    unittest.main()
