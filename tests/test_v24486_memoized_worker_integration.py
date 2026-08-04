from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24469_bounded_worker_supervisor import (  # noqa: E402
    read_checkpoints,
)
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    CERTIFICATE_NAME,
)
from deepwide_agent.v24486_memoized_worker_integration import (  # noqa: E402
    run_memoized_worker,
    validate_memo_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24486-test-validator-manifest").hexdigest()


def writer(directory: Path):
    def write(name: str, value) -> None:
        _new_json(directory / name, value)

    return write


class V24486MemoizedWorkerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.output_root = Path(self.temporary.name)
        self.directory = self.output_root / "task"
        self.checkpoint = self.output_root / "checkpoint"
        self.fixture = self.output_root / "fixture"
        self.directory.mkdir()
        self.checkpoint.mkdir()
        self.fixture.mkdir()

    def run_success(self) -> tuple[dict, float]:
        clock = AdvancingClock()
        model, search = clients(self.fixture, clock, third=True)
        started = time.perf_counter()
        receipt = run_memoized_worker(
            TASK,
            ordinal=1,
            expected_supervisor_pid=os.getppid(),
            checkpoint_directory=self.checkpoint,
            output_root=self.output_root,
            directory=self.directory,
            model_factory=lambda _callback: model,
            search_factory=lambda _callback: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(self.directory),
            validator_manifest_sha256=MANIFEST,
        )
        return receipt, time.perf_counter() - started

    def test_full_worker_preserves_exact_surface_and_validates_memo(self) -> None:
        receipt, elapsed = self.run_success()
        validate_memo_receipt(receipt)
        self.assertEqual(receipt["total_misses"], 8)
        self.assertGreater(receipt["total_hits"], 100)
        self.assertEqual(receipt["total_mismatches"], 0)
        self.assertTrue(receipt["bindings_restored"])
        self.assertLess(elapsed, 5.0)
        self.assertEqual(
            {path.name for path in self.directory.iterdir()},
            {
                MODEL_NAME,
                TRANSPORT_NAME,
                SEARCH_NAME,
                RESULT_NAME,
                CERTIFICATE_NAME,
                CHILD_NAME,
            },
        )
        child = validate_child_receipt(
            json.loads((self.directory / CHILD_NAME).read_text(encoding="utf-8"))
        )
        self.assertIsNone(child["exception_type"])
        checkpoints = read_checkpoints(self.checkpoint, ordinal=1)
        self.assertEqual(checkpoints[-1]["stage"], "worker_complete")

    def test_invalid_memo_receipt_fails_before_success_terminal(self) -> None:
        clock = AdvancingClock()
        model, search = clients(self.fixture, clock, third=True)
        with patch(
            "deepwide_agent.v24486_memoized_worker_integration.validate_memo_receipt",
            side_effect=ValueError("synthetic memo rejection"),
        ):
            with self.assertRaisesRegex(ValueError, "synthetic memo rejection"):
                run_memoized_worker(
                    TASK,
                    ordinal=1,
                    expected_supervisor_pid=os.getppid(),
                    checkpoint_directory=self.checkpoint,
                    output_root=self.output_root,
                    directory=self.directory,
                    model_factory=lambda _callback: model,
                    search_factory=lambda _callback: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(self.directory),
                    validator_manifest_sha256=MANIFEST,
                )
        child = validate_child_receipt(
            json.loads((self.directory / CHILD_NAME).read_text(encoding="utf-8"))
        )
        self.assertEqual(child["stage"], "child_exception")
        self.assertEqual(child["exception_type"], "ValidationError")
        checkpoints = read_checkpoints(self.checkpoint, ordinal=1)
        self.assertNotEqual(checkpoints[-1]["stage"], "worker_complete")

    def test_receipt_tamper_fails_closed(self) -> None:
        receipt, _ = self.run_success()
        for field, value in (
            ("total_misses", 7),
            ("total_hits", 0),
            ("total_mismatches", 1),
            ("bindings_restored", False),
        ):
            with self.subTest(field=field):
                altered = dict(receipt)
                altered[field] = value
                with self.assertRaises(ValueError):
                    validate_memo_receipt(altered)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24486_memoized_worker_integration.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
