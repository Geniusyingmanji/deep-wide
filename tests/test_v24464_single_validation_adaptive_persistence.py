from __future__ import annotations

import hashlib
import json
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

from deepwide_agent.v24308_child_exit_observability import child_receipt  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import CHILD_NAME  # noqa: E402
from deepwide_agent.v24457_adaptive_entropy_support import build_envelope  # noqa: E402
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    validate_proof_carrying_adaptive_bundle,
)
from deepwide_agent.v24460_adaptive_capability_projection import task_projection  # noqa: E402
from deepwide_agent.v24464_single_validation_adaptive_persistence import (  # noqa: E402
    ValidatedAdaptiveExecution,
    build_envelope_from_validated_execution,
    run_and_persist_single_validation_adaptive_task,
    run_single_validation_v24457_task,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24464-test-validator-manifest").hexdigest()


def writer(directory: Path):
    def write(name, value):
        path = directory / name
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return write


class V24464SingleValidationAdaptivePersistenceTests(unittest.TestCase):
    def run_fixture(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock, third=True)
        validated = run_single_validation_v24457_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return Path(temporary.name), validated

    def test_mechanical_envelope_is_byte_value_equal_to_frozen_builder(self) -> None:
        _, validated = self.run_fixture()
        self.assertIsInstance(validated, ValidatedAdaptiveExecution)
        fast = build_envelope_from_validated_execution(validated)
        slow = build_envelope(validated._trusted_outcome())
        self.assertEqual(fast, slow)

    def test_fast_builder_does_not_call_recursive_adaptive_validator(self) -> None:
        _, validated = self.run_fixture()
        with patch(
            "deepwide_agent.v24457_adaptive_entropy_support.validate_envelope",
            side_effect=AssertionError("recursive replay"),
        ), patch(
            "deepwide_agent.v24457_adaptive_entropy_support.validate_cross_artifacts",
            side_effect=AssertionError("recursive replay"),
        ):
            envelope = build_envelope_from_validated_execution(validated)
        self.assertEqual(envelope["adaptive_result"], validated._trusted_outcome().adaptive_result)

    def test_capability_cannot_be_forged(self) -> None:
        with self.assertRaises(TypeError):
            ValidatedAdaptiveExecution(object())
        with self.assertRaises(TypeError):
            build_envelope_from_validated_execution(object())  # type: ignore[arg-type]

    def test_persistence_writes_certificate_and_parent_accepts_capability(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=ROOT / "outputs"
        ) as temporary, tempfile.TemporaryDirectory(dir=ROOT / "outputs") as fixture:
            directory = Path(temporary)
            clock = AdvancingClock()
            # Client caches are deliberately outside the exact terminal
            # surface, matching the external child layout.
            model, search = clients(Path(fixture), clock, third=True)
            outcome = run_and_persist_single_validation_adaptive_task(
                TASK,
                model_factory=lambda: model,
                search_factory=lambda: search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                directory=directory,
                writer=writer(directory),
                validator_manifest_sha256=MANIFEST,
            )
            writer(directory)(
                CHILD_NAME,
                child_receipt(
                    stage="result_envelope_written",
                    exception_type=None,
                    model_receipt_written=True,
                    transport_receipt_written=True,
                    result_envelope_written=True,
                ),
            )
            value = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            capability = validate_proof_carrying_adaptive_bundle(
                value,
                directory=directory,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
            )
            projected = task_projection(1, capability)
            self.assertEqual(
                projected["adaptive_final_decision_credit_total_nats"],
                outcome.adaptive_result["adaptive_support_receipt"][
                    "final_decision_credit_total_nats"
                ],
            )

    def test_fast_builder_has_bounded_local_wall(self) -> None:
        _, validated = self.run_fixture()
        started = time.perf_counter()
        build_envelope_from_validated_execution(validated)
        self.assertLess(time.perf_counter() - started, 1.0)


if __name__ == "__main__":
    unittest.main()
