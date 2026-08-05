from __future__ import annotations

import argparse
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

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
)
from deepwide_agent.v24505_record_bound_timed_parent import (  # noqa: E402
    run_record_bound_parent_with_separated_budget,
    supervise_record_bound_worker_with_separated_budget,
)
from deepwide_agent.v24511_proposal_seeded_record_bound_worker import (  # noqa: E402
    run_proposal_seeded_record_bound_worker,
    validate_combined_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import (  # noqa: E402
    clients as parent_clients,
)
from test_v24503_record_bound_reserve_integration import (  # noqa: E402
    RecordReserveSearch,
)


MANIFEST = hashlib.sha256(b"v24511-test-validator-manifest").hexdigest()
BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2024 |
```"""


class ProposalOnlySearch(RecordReserveSearch):
    """Proposal support, no active support, then targeted/reserve support."""

    def fetch_urls(self, requests_):
        batches = super().fetch_urls(requests_)
        if self.fetch_invocations in {1, 2}:
            content = "Alpha was founded in 2025."
        elif self.fetch_invocations == 3:
            content = "Alpha publishes documentation."
        else:
            return batches
        for batch in batches:
            for result in batch["results"]:
                result["raw_content"] = content
        return batches


def clients(output: Path, clock: AdvancingClock):
    model, old_search = parent_clients(output, clock, third=False)
    model.inner.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    model.inner.baseline = BASELINE
    search = ProposalOnlySearch(
        clock, deadline=300, record_mode="split_support"
    )
    search.timeout = MAXIMUM_PROVIDER_EFFECT_SECONDS
    search.static_search_timeout_seconds = MAXIMUM_PROVIDER_EFFECT_SECONDS
    del old_search
    return model, search


def writer(directory: Path):
    return lambda name, value: _new_json(directory / name, value)


def process_mode(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    fixture = Path(args.fixture)
    if args.command == "worker":
        clock = AdvancingClock()
        model, search = clients(fixture, clock)
        run_proposal_seeded_record_bound_worker(
            TASK,
            ordinal=1,
            expected_supervisor_pid=int(
                os.environ["DEEPWIDE_EXPECTED_SUPERVISOR_PID"]
            ),
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
    worker_command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(Path(__file__).resolve()),
        "worker",
        "--output-root",
        str(output_root),
        "--directory",
        str(directory),
        "--checkpoint-directory",
        str(checkpoint),
        "--fixture",
        str(fixture),
    ]
    supervise_record_bound_worker_with_separated_budget(
        ordinal=1,
        cwd=ROOT,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint,
        worker_command=worker_command,
        deadline_origin=args.deadline_origin_monotonic,
        expected_model_cap=2,
        writer=writer(directory),
    )
    return 0


class V24511ProposalSeededRecordBoundWorkerTests(unittest.TestCase):
    def test_worker_converts_proposal_only_dead_zone_and_preserves_surface(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir(); checkpoint.mkdir(); fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock)
            with patch(
                "deepwide_agent.v24511_proposal_seeded_record_bound_worker.bind_worker_to_parent"
            ):
                receipt = run_proposal_seeded_record_bound_worker(
                    TASK,
                    ordinal=1,
                    expected_supervisor_pid=os.getpid(),
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
            result = json.loads((directory / RESULT_NAME).read_text())
            surface = {path.name for path in directory.iterdir()}
        validated = validate_combined_receipt(receipt)
        planner = validated["proposal_seeded_planner_receipt"]
        self.assertEqual(planner["proposal_seeded_plan_builds"], 1)
        record = result["record_bound_result"]["record_bound_receipt"]
        self.assertGreaterEqual(record["added_observation_count"], 1)
        self.assertEqual(record["safe_change_improvement_count"], 1)
        self.assertGreater(record["decision_credit_gain_nats"], 0)
        self.assertIn("| Alpha | 2025 |", result["record_bound_result"]["candidate_prediction"])
        self.assertNotIn("proposal_seeded_planner_receipt.json", surface)

    def test_invalid_planner_receipt_fails_before_success_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir(); checkpoint.mkdir(); fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock)
            with (
                patch(
                    "deepwide_agent.v24511_proposal_seeded_record_bound_worker.bind_worker_to_parent"
                ),
                patch(
                    "deepwide_agent.v24511_proposal_seeded_record_bound_worker.validate_planner_receipt",
                    side_effect=ValueError("invalid planner receipt"),
                ),
                self.assertRaisesRegex(ValueError, "invalid planner receipt"),
            ):
                run_proposal_seeded_record_bound_worker(
                    TASK,
                    ordinal=1,
                    expected_supervisor_pid=os.getpid(),
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
            terminal = json.loads(
                (directory / "child_terminal_receipt.json").read_text()
            )
        self.assertEqual(terminal["stage"], "child_exception")
        self.assertFalse(terminal["result_envelope_written"])

    def test_real_parent_supervisor_worker_chain_consumes_capability(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir(); checkpoint.mkdir(); fixture.mkdir()
            command = [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                str(Path(__file__).resolve()),
                "supervisor",
                "--output-root",
                str(output_root),
                "--directory",
                str(directory),
                "--checkpoint-directory",
                str(checkpoint),
                "--fixture",
                str(fixture),
            ]
            started = time.monotonic()
            outcome = run_record_bound_parent_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=output_root,
                directory=directory,
                checkpoint_directory=checkpoint,
                supervisor_command=command,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
            )
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 70.0)
        self.assertEqual(
            outcome.proof.parent_receipt["failure_taxonomy"], "success"
        )
        self.assertTrue(outcome.proof.adaptive_projection["passed"])
        self.assertGreater(
            outcome.proof.adaptive_projection["decision_credit_gain_nats"], 0
        )
        self.assertEqual(
            outcome.supervision_receipt["last_stage"], "worker_complete"
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/v24511_proposal_seeded_record_bound_worker.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"worker", "supervisor"}:
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--output-root", required=True)
        parser.add_argument("--directory", required=True)
        parser.add_argument("--checkpoint-directory", required=True)
        parser.add_argument("--fixture", required=True)
        parser.add_argument("--deadline-origin-monotonic")
        raise SystemExit(process_mode(parser.parse_args()))
    unittest.main()
