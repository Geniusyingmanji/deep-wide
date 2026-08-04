from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24469_bounded_worker_supervisor import (  # noqa: E402
    StageJournal,
    bind_worker_to_parent,
)
from deepwide_agent.v24470_bounded_adaptive_integration import (  # noqa: E402
    SUPERVISION_RECEIPT_NAME,
    aggregate_supervision_receipts,
    build_hard_total_wall_model,
    build_hard_total_wall_search,
    run_bounded_parent_subprocess,
    run_worker,
    supervise_and_publish,
    validate_bounded_supervision_receipt,
    validate_supervision_aggregate,
)
from test_v24343_semantic_active_runner import slots  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24470-test-validator-manifest").hexdigest()


def writer(directory: Path):
    def write(name: str, value) -> None:
        _new_json(directory / name, value)

    return write


def run_worker_mode(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    output_root = Path(args.output_root)
    fixture = Path(args.fixture)
    expected = int(os.environ["DEEPWIDE_EXPECTED_SUPERVISOR_PID"])
    if args.behavior == "timeout":
        bind_worker_to_parent(expected_parent_pid=expected)
        journal = StageJournal(checkpoint, ordinal=1)
        journal.record("worker_entered")
        journal.record(args.stage)
        time.sleep(10)
        return 7
    clock = AdvancingClock()
    model, search = clients(fixture, clock, third=True)
    run_worker(
        TASK,
        ordinal=1,
        expected_supervisor_pid=expected,
        checkpoint_directory=checkpoint,
        output_root=output_root,
        directory=directory,
        model_factory=lambda _callback: model,
        search_factory=lambda _callback: search,
        partition_seed_sha256=SEED,
        limits=limits(),
        monotonic=clock,
        expected_model_cap=2,
        writer=writer(directory),
        validator_manifest_sha256=MANIFEST,
    )
    return 0


def run_supervisor_mode(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(Path(__file__).resolve()),
        "worker",
        "--behavior",
        args.behavior,
        "--stage",
        args.stage,
        "--directory",
        str(directory),
        "--checkpoint-directory",
        str(checkpoint),
        "--output-root",
        args.output_root,
        "--fixture",
        args.fixture,
    ]
    supervise_and_publish(
        ordinal=1,
        cwd=ROOT,
        output_root=Path(args.output_root),
        directory=directory,
        checkpoint_directory=checkpoint,
        command=command,
        timeout_seconds=float(args.worker_timeout),
        expected_model_cap=2,
        writer=writer(directory),
    )
    return 0


class V24470BoundedAdaptiveIntegrationTests(unittest.TestCase):
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

    def command(
        self,
        *,
        behavior: str,
        stage: str = "complete_validation_entered",
        worker_timeout: float,
    ) -> list[str]:
        return [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(Path(__file__).resolve()),
            "supervisor",
            "--behavior",
            behavior,
            "--stage",
            stage,
            "--worker-timeout",
            str(worker_timeout),
            "--directory",
            str(self.directory),
            "--checkpoint-directory",
            str(self.checkpoint),
            "--output-root",
            str(self.output_root),
            "--fixture",
            str(self.fixture),
        ]

    def test_full_success_crosses_worker_supervisor_and_parent_proof(self) -> None:
        started = time.monotonic()
        value = run_bounded_parent_subprocess(
            ordinal=1,
            cwd=ROOT,
            output_root=self.output_root,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command(behavior="success", worker_timeout=90),
            parent_timeout_seconds=120,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 120)
        self.assertEqual(value.proof.parent_receipt["failure_taxonomy"], "success")
        self.assertTrue(value.proof.adaptive_projection["passed"])
        receipt = value.supervision_receipt
        self.assertFalse(receipt["worker_hard_timeout"])
        self.assertEqual(receipt["return_code"], 0)
        self.assertEqual(receipt["last_stage"], "worker_complete")
        self.assertTrue(receipt["complete_validation_entered"])
        self.assertTrue(receipt["complete_validation_returned"])
        self.assertGreater(receipt["last_stage_sequence"], 5)
        # The in-memory worker already ran the complete frozen validator once;
        # the serialized surface is intentionally checked by the exact-byte
        # V2.44.59 certificate/capability path above.  Replaying the in-memory
        # validator on JSON would conflate tuple/list serialization identity.
        self.assertEqual(
            value.proof.timing_receipt[
                "child_complete_semantic_validation_attested"
            ],
            True,
        )
        self.assertEqual(
            value.proof.timing_receipt["certificate_validation_invocations"],
            1,
        )
        aggregate = aggregate_supervision_receipts([receipt], selected=1)
        self.assertEqual(aggregate["worker_success_tasks"], 1)
        self.assertEqual(aggregate["complete_validation_returned_tasks"], 1)
        self.assertEqual(
            {path.name for path in self.checkpoint.iterdir()},
            {SUPERVISION_RECEIPT_NAME},
        )

    def test_worker_timeout_closes_before_parent_and_preserves_stage(self) -> None:
        started = time.monotonic()
        value = run_bounded_parent_subprocess(
            ordinal=1,
            cwd=ROOT,
            output_root=self.output_root,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command(
                behavior="timeout",
                stage="complete_validation_entered",
                worker_timeout=0.35,
            ),
            parent_timeout_seconds=3,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 2)
        self.assertEqual(
            value.proof.parent_receipt["failure_taxonomy"],
            "child_nonzero_with_terminal_receipt",
        )
        self.assertFalse(value.proof.adaptive_projection["passed"])
        receipt = value.supervision_receipt
        self.assertTrue(receipt["worker_hard_timeout"])
        self.assertEqual(receipt["last_stage"], "complete_validation_entered")
        self.assertTrue(receipt["complete_validation_entered"])
        self.assertFalse(receipt["complete_validation_returned"])
        self.assertTrue(receipt["failure_snapshot_written"])
        aggregate = aggregate_supervision_receipts([receipt], selected=1)
        self.assertEqual(aggregate["worker_hard_timeout_tasks"], 1)
        self.assertEqual(
            aggregate["last_stage_counts"], {"complete_validation_entered": 1}
        )

    def test_supervision_aggregate_rejects_resealed_stage_tamper(self) -> None:
        from deepwide_agent.v24469_bounded_worker_supervisor import build_worker_receipt

        receipt = build_worker_receipt(
            ordinal=1,
            last_stage="model_effect_started",
            last_stage_sequence=2,
            worker_hard_timeout=True,
            failure_snapshot_written=True,
            checkpoints=[],
            checkpoint_chain_valid=False,
            elapsed_seconds=1,
            return_code=None,
        )
        # A chain-invalid receipt cannot claim observed lower bounds, but it is
        # still aggregatable as an untrusted-stage failure row.
        receipt["last_stage"] = None
        receipt["last_stage_sequence"] = 0
        receipt.pop("receipt_payload_sha256")
        from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256

        receipt["receipt_payload_sha256"] = payload_sha256(receipt)
        validate_bounded_supervision_receipt(receipt)
        aggregate = aggregate_supervision_receipts([receipt], selected=1)
        altered = dict(aggregate)
        altered["last_stage_counts"] = {"private-stage": 1}
        altered.pop("aggregate_payload_sha256")
        altered["aggregate_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_supervision_aggregate(altered)

    def test_chain_invalid_receipt_cannot_claim_resealed_effect_lower_bound(self) -> None:
        from deepwide_agent.v24469_bounded_worker_supervisor import build_worker_receipt
        from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256

        receipt = build_worker_receipt(
            ordinal=1,
            last_stage=None,
            last_stage_sequence=0,
            worker_hard_timeout=True,
            failure_snapshot_written=True,
            checkpoints=[],
            checkpoint_chain_valid=False,
            elapsed_seconds=1,
            return_code=None,
        )
        validate_bounded_supervision_receipt(receipt)
        for field, value in (
            ("last_stage", "model_effect_started"),
            ("model_effect_started_lower_bound", 1),
            ("complete_validation_entered", True),
        ):
            with self.subTest(field=field):
                altered = dict(receipt)
                altered[field] = value
                if field == "last_stage":
                    altered["last_stage_sequence"] = 1
                altered.pop("receipt_payload_sha256")
                altered["receipt_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_bounded_supervision_receipt(altered)

    def test_real_total_wall_factories_bind_stage_callbacks(self) -> None:
        from deepwide_agent.v24470_bounded_adaptive_integration import (
            HardTotalWallUncertaintyNativeSearchClient,
        )

        events: list[str] = []
        slot_directory = slots(self.output_root)
        model = build_hard_total_wall_model(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=1,
            max_retries=1,
            slot_directory=slot_directory,
            output_root=self.output_root,
            slot_cap=2,
            absolute_deadline=time.monotonic() + 5,
            cleanup_reserve_seconds=1,
            minimum_attempt_seconds=0.01,
            stage_callback=events.append,
        )
        search = build_hard_total_wall_search(
            url="http://127.0.0.1:9/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=1,
            max_retries=1,
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=time.monotonic() + 5,
            cleanup_reserve_seconds=1,
            minimum_attempt_seconds=0.01,
            stage_callback=events.append,
        )
        self.assertIsInstance(search, HardTotalWallUncertaintyNativeSearchClient)
        self.assertEqual(model.absolute_deadline, model.inner.absolute_deadline)
        model.inner._stage_callback("model_effect_started")
        search._stage_callback("hosted_search_effect_started")
        self.assertEqual(
            events, ["model_effect_started", "hosted_search_effect_started"]
        )

    def test_layout_rejects_checkpoint_inside_task_before_subprocess(self) -> None:
        nested = self.directory / "checkpoint"
        nested.mkdir()
        with self.assertRaisesRegex(RuntimeError, "siblings"):
            run_bounded_parent_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=self.output_root,
                directory=self.directory,
                checkpoint_directory=nested,
                command=["must-not-run"],
                parent_timeout_seconds=1,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
            )

    def test_stage_hook_monkeypatch_is_restored_after_failure(self) -> None:
        from deepwide_agent import v24457_adaptive_entropy_support as adaptive
        from deepwide_agent.v24470_bounded_adaptive_integration import (
            run_stage_hooked_single_validation,
        )

        original_run = adaptive.parent.run_v24447_task
        original_build = adaptive.parent.build_envelope
        with patch.object(
            adaptive,
            "run_v24457_task",
            side_effect=RuntimeError("synthetic failure"),
        ):
            with self.assertRaises(RuntimeError):
                run_stage_hooked_single_validation(
                    TASK,
                    model=object(),
                    search=object(),
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=time.monotonic,
                    stage_callback=lambda _stage: None,
                )
        self.assertIs(adaptive.parent.run_v24447_task, original_run)
        self.assertIs(adaptive.parent.build_envelope, original_build)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24465_single_validation_adaptive_build as audit

        accesses, imports = audit.base._ast_findings(
            Path("src/deepwide_agent/v24470_bounded_adaptive_integration.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"worker", "supervisor"}:
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--behavior", required=True)
        parser.add_argument("--stage", required=True)
        parser.add_argument("--worker-timeout", default="90")
        parser.add_argument("--directory", required=True)
        parser.add_argument("--checkpoint-directory", required=True)
        parser.add_argument("--output-root", required=True)
        parser.add_argument("--fixture", required=True)
        args = parser.parse_args()
        code = (
            run_worker_mode(args)
            if args.command == "worker"
            else run_supervisor_mode(args)
        )
        raise SystemExit(code)
    unittest.main()


if __name__ == "__main__":
    main()
