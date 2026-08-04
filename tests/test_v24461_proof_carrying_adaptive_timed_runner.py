from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import child_receipt  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    build_envelope,
    run_v24457_task,
)
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    CERTIFICATE_NAME,
    build_terminal_certificate,
)
from deepwide_agent.v24461_proof_carrying_adaptive_timed_runner import (  # noqa: E402
    aggregate_stage_timings,
    run_proof_carrying_adaptive_timed_subprocess,
    validate_stage_timing_aggregate,
    validate_timing_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24461-test-validator-manifest").hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class SuccessfulPopen:
    def __init__(self, *_args, **_kwargs):
        self.pid = 987661
        self.returncode = 0

    def wait(self, timeout=None):
        del timeout
        return 0


class NonzeroPopen:
    def __init__(self, *_args, **_kwargs):
        self.pid = 987662
        self.returncode = 1

    def wait(self, timeout=None):
        del timeout
        return 1


class V24461ProofCarryingAdaptiveTimedRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.fixture_root.name), clock, third=True)
        cls.outcome = run_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(cls.outcome)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_root.cleanup()

    def populate_success(self, directory: Path) -> None:
        artifacts = {
            RESULT_NAME: self.envelope,
            MODEL_NAME: self.outcome.model_slot_receipt,
            TRANSPORT_NAME: self.outcome.transport_health,
            SEARCH_NAME: self.outcome.search_single_shot_receipt,
        }
        for name, value in artifacts.items():
            write_json(directory / name, value)
        certificate = build_terminal_certificate(
            directory,
            self.outcome,
            validator_manifest_sha256=MANIFEST,
            expected_artifacts=artifacts,
        )
        write_json(directory / CERTIFICATE_NAME, certificate)
        write_json(
            directory / CHILD_NAME,
            child_receipt(
                stage="result_envelope_written",
                exception_type=None,
                model_receipt_written=True,
                transport_receipt_written=True,
                result_envelope_written=True,
            ),
        )

    def run_case(self, directory: Path, *, ordinal: int, popen):
        return run_proof_carrying_adaptive_timed_subprocess(
            ordinal=ordinal,
            cwd=ROOT,
            output_root=ROOT / "outputs",
            directory=directory,
            command=["synthetic"],
            environment={},
            timeout_seconds=1,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
            popen=popen,
        )

    def test_success_uses_capability_for_observation_and_projection(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate_success(directory)
            outcome = self.run_case(directory, ordinal=1, popen=SuccessfulPopen)
            timing = validate_timing_receipt(outcome.timing_receipt)
            self.assertEqual(outcome.parent_receipt["failure_taxonomy"], "success")
            self.assertEqual(
                outcome.observation["effect_scope"], "successful_terminal_receipts"
            )
            self.assertTrue(outcome.adaptive_projection["passed"])
            self.assertEqual(timing["certificate_validation_invocations"], 1)
            self.assertEqual(timing["adaptive_projection_invocations"], 1)
            self.assertFalse(
                timing["parent_recursive_historical_semantic_replay_performed"]
            )

    def test_nonzero_child_preserves_failure_lower_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            write_json(
                directory / CHILD_NAME,
                child_receipt(
                    stage="child_exception",
                    exception_type="RuntimeError",
                    model_receipt_written=False,
                    transport_receipt_written=False,
                    result_envelope_written=False,
                ),
            )
            outcome = self.run_case(directory, ordinal=1, popen=NonzeroPopen)
            timing = validate_timing_receipt(outcome.timing_receipt)
            self.assertEqual(
                outcome.parent_receipt["failure_taxonomy"],
                "child_nonzero_with_terminal_receipt",
            )
            self.assertEqual(outcome.observation["effect_scope"], "unobserved_lower_bound")
            self.assertFalse(outcome.adaptive_projection["passed"])
            self.assertEqual(timing["certificate_validation_invocations"], 0)
            self.assertEqual(timing["adaptive_projection_invocations"], 0)
            self.assertTrue(
                timing["failure_observation_uses_partial_effect_lower_bound_path"]
            )

    def test_success_surface_extra_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate_success(directory)
            write_json(directory / "unexpected.json", {})
            outcome = self.run_case(directory, ordinal=1, popen=SuccessfulPopen)
            self.assertEqual(
                outcome.parent_receipt["failure_taxonomy"],
                "result_envelope_invalid",
            )
            self.assertFalse(outcome.adaptive_projection["passed"])
            self.assertTrue(
                outcome.timing_receipt[
                    "failure_observation_uses_partial_effect_lower_bound_path"
                ]
            )

    def test_aggregate_conserves_success_failure_and_zero_replay(self) -> None:
        timings = []
        for ordinal, process in ((1, SuccessfulPopen), (2, NonzeroPopen)):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                directory = Path(temporary)
                if process is SuccessfulPopen:
                    self.populate_success(directory)
                else:
                    write_json(
                        directory / CHILD_NAME,
                        child_receipt(
                            stage="child_exception",
                            exception_type="RuntimeError",
                            model_receipt_written=False,
                            transport_receipt_written=False,
                            result_envelope_written=False,
                        ),
                    )
                timings.append(
                    self.run_case(directory, ordinal=ordinal, popen=process).timing_receipt
                )
        aggregate = validate_stage_timing_aggregate(
            aggregate_stage_timings(timings, selected=2)
        )
        self.assertEqual(aggregate["parent_success_tasks"], 1)
        self.assertEqual(aggregate["parent_failure_tasks"], 1)
        self.assertEqual(aggregate["capability_adaptive_projection_tasks"], 1)
        self.assertEqual(aggregate["failure_lower_bound_observation_tasks"], 1)
        self.assertEqual(aggregate["recursive_historical_semantic_replay_tasks"], 0)

    def test_timing_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate_success(directory)
            value = self.run_case(
                directory, ordinal=1, popen=SuccessfulPopen
            ).timing_receipt
            value["parent_recursive_historical_semantic_replay_performed"] = True
            with self.assertRaises(ValueError):
                validate_timing_receipt(value)


if __name__ == "__main__":
    unittest.main()
