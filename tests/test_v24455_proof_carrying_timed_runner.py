from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
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
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24454_proof_carrying_third_source_envelope import (  # noqa: E402
    CERTIFICATE_NAME,
    build_terminal_certificate,
)
from deepwide_agent.v24455_proof_carrying_timed_runner import (  # noqa: E402
    aggregate_stage_timings,
    run_proof_carrying_timed_observed_subprocess,
    validate_stage_timing_aggregate,
    validate_timing_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24455-test-validator-manifest").hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class SuccessfulPopen:
    def __init__(self, *_args, **_kwargs):
        self.pid = 987654
        self.returncode = 0

    def wait(self, timeout=None):
        del timeout
        return 0


class NonzeroPopen:
    def __init__(self, *_args, **_kwargs):
        self.pid = 987655
        self.returncode = 1

    def wait(self, timeout=None):
        del timeout
        return 1


class V24455ProofCarryingTimedRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.fixture_root.name), clock, third=True)
        cls.outcome = run_v24447_task(
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

    def test_success_projects_observation_and_mechanism_from_one_capability(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate_success(directory)
            value = run_proof_carrying_timed_observed_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=directory,
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
                popen=SuccessfulPopen,
            )
            timing = validate_timing_receipt(value.timing_receipt)
            self.assertEqual(value.parent_receipt["failure_taxonomy"], "success")
            self.assertEqual(value.observation["effect_scope"], "successful_terminal_receipts")
            self.assertTrue(value.mechanism_projection["passed"])
            self.assertEqual(timing["certificate_validation_invocations"], 1)
            self.assertEqual(timing["observation_projection_invocations"], 1)
            self.assertEqual(timing["mechanism_projection_invocations"], 1)
            self.assertTrue(
                timing[
                    "observation_consumed_only_validated_capability_receipts_on_success"
                ]
            )
            self.assertFalse(
                timing["parent_recursive_historical_semantic_replay_performed"]
            )
            self.assertLess(
                timing["parent_certificate_validation_wall_seconds"], 1.0
            )

    def test_nonzero_child_uses_failure_lower_bound_observation(self) -> None:
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
            value = run_proof_carrying_timed_observed_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=directory,
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
                popen=NonzeroPopen,
            )
            timing = validate_timing_receipt(value.timing_receipt)
            self.assertEqual(
                value.parent_receipt["failure_taxonomy"],
                "child_nonzero_with_terminal_receipt",
            )
            self.assertEqual(value.observation["effect_scope"], "unobserved_lower_bound")
            self.assertFalse(value.mechanism_projection["passed"])
            self.assertEqual(timing["certificate_validation_invocations"], 0)
            self.assertEqual(timing["mechanism_projection_invocations"], 0)
            self.assertTrue(
                timing["failure_observation_uses_partial_effect_lower_bound_path"]
            )

    def test_success_surface_extra_file_is_rejected_after_parent_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate_success(directory)
            write_json(directory / "unexpected.json", {})
            value = run_proof_carrying_timed_observed_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=directory,
                command=["synthetic"],
                environment={},
                timeout_seconds=1,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
                popen=SuccessfulPopen,
            )
            self.assertEqual(
                value.parent_receipt["failure_taxonomy"],
                "result_envelope_invalid",
            )
            self.assertEqual(
                value.timing_receipt["certificate_validation_invocations"], 1
            )
            self.assertFalse(
                value.timing_receipt[
                    "parent_exact_surface_and_certificate_validated_once"
                ]
            )
            self.assertTrue(
                value.timing_receipt[
                    "failure_observation_uses_partial_effect_lower_bound_path"
                ]
            )

    def test_aggregate_conserves_success_failure_and_zero_replay(self) -> None:
        receipts = []
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
                receipts.append(
                    run_proof_carrying_timed_observed_subprocess(
                        ordinal=ordinal,
                        cwd=ROOT,
                        output_root=ROOT / "outputs",
                        directory=directory,
                        command=["synthetic"],
                        environment={},
                        timeout_seconds=1,
                        expected_model_cap=2,
                        expected_validator_manifest_sha256=MANIFEST,
                        popen=process,
                    ).timing_receipt
                )
        aggregate = aggregate_stage_timings(receipts, selected=2)
        validate_stage_timing_aggregate(aggregate)
        self.assertEqual(aggregate["parent_success_tasks"], 1)
        self.assertEqual(aggregate["parent_failure_tasks"], 1)
        self.assertEqual(aggregate["certificate_validated_once_tasks"], 1)
        self.assertEqual(aggregate["failure_lower_bound_observation_tasks"], 1)
        self.assertEqual(aggregate["recursive_historical_semantic_replay_tasks"], 0)

    def test_real_parent_validation_p95_is_below_frozen_ceiling(self) -> None:
        durations = []
        for ordinal in range(1, 6):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                directory = Path(temporary)
                self.populate_success(directory)
                started = time.perf_counter()
                value = run_proof_carrying_timed_observed_subprocess(
                    ordinal=ordinal,
                    cwd=ROOT,
                    output_root=ROOT / "outputs",
                    directory=directory,
                    command=["synthetic"],
                    environment={},
                    timeout_seconds=1,
                    expected_model_cap=2,
                    expected_validator_manifest_sha256=MANIFEST,
                    popen=SuccessfulPopen,
                )
                durations.append(
                    value.timing_receipt[
                        "parent_certificate_validation_wall_seconds"
                    ]
                )
                self.assertLess(time.perf_counter() - started, 1.0)
        self.assertLess(max(durations), 1.0)


if __name__ == "__main__":
    unittest.main()
