from __future__ import annotations

import copy
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

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24415_effect_equivalent_structured_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_envelope,
    run_and_persist_effect_equivalent_task,
    run_v24415_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24409_structured_uncertainty_runner import StructuredDeadlineSearch  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import (  # noqa: E402
    AdvancingClock,
    clients as advancing_clients,
)


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


class V24415EffectEquivalentStructuredRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def run_case(self):
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = advancing_clients(output, clock)
        outcome = run_v24415_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search, output

    def test_advancing_clock_now_succeeds_with_replayable_equivalence(self) -> None:
        outcome, model, search, _ = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        equivalence = outcome.effect_equivalence_receipt
        self.assertGreater(
            equivalence["model_remaining_seconds_before"],
            equivalence["model_remaining_seconds_after"],
        )
        self.assertFalse(equivalence["external_effect_detected"])
        self.assertEqual(model.acquisitions, outcome.model_slot_receipt["acquisitions"])
        self.assertEqual(search.fetch_invocations, 3)

    def test_before_after_snapshot_or_attestation_tamper_fails(self) -> None:
        outcome, _, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        for field in ("before", "after", "attestation"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                if field == "before":
                    altered["model_slot_receipt_before_recovery"][
                        "remaining_seconds_at_receipt"
                    ] += 1.0
                    receipt = altered["model_slot_receipt_before_recovery"]
                    receipt.pop("receipt_payload_sha256")
                    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
                elif field == "after":
                    altered["transport_health"]["hard_fetch_helper_calls"] += 1
                else:
                    altered["effect_equivalence_receipt"][
                        "model_remaining_seconds_after"
                    ] += 0.001
                    receipt = altered["effect_equivalence_receipt"]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_envelope(altered)

    def test_privileged_input_rejected_before_effect(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = advancing_clients(output, clock)
        with self.assertRaises(ValueError):
            run_v24415_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_success_persists_post_recovery_terminal_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = advancing_clients(output, clock)
        outcome = run_and_persist_effect_equivalent_task(
            TASK,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(output),
        )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            self.assertTrue((output / name).is_file())
        self.assertFalse((output / FAILURE_NAME).exists())
        self.assertEqual(
            json.loads((output / MODEL_NAME).read_text(encoding="utf-8")),
            outcome.model_slot_receipt,
        )

    def test_recovery_failure_preserves_partial_effect_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = advancing_clients(output, clock)
        with patch(
            "deepwide_agent.v24415_effect_equivalent_structured_runner.recover_structured_uncertainty",
            side_effect=RuntimeError("private detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_effect_equivalent_task(
                    TASK,
                    model_factory=lambda: model,
                    search_factory=lambda: search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                    expected_model_cap=2,
                    writer=writer(output),
                )
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, FAILURE_NAME):
            self.assertTrue((output / name).is_file())
        self.assertFalse((output / RESULT_NAME).exists())
        snapshot = json.loads((output / FAILURE_NAME).read_text(encoding="utf-8"))
        self.assertEqual(snapshot["failure_stage"], "runtime")
        self.assertNotIn("private detail", json.dumps(snapshot))

    def test_serialization_failure_binds_only_durable_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = advancing_clients(output, clock)
        ordinary = writer(output)

        def fail_after_model(name: str, value) -> None:
            if name == TRANSPORT_NAME:
                raise OSError("private serialization detail")
            ordinary(name, value)

        with self.assertRaises(OSError):
            run_and_persist_effect_equivalent_task(
                TASK,
                model_factory=lambda: model,
                search_factory=lambda: search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                writer=fail_after_model,
            )
        self.assertTrue((output / MODEL_NAME).is_file())
        self.assertFalse((output / TRANSPORT_NAME).exists())
        snapshot = json.loads((output / FAILURE_NAME).read_text(encoding="utf-8"))
        self.assertTrue(snapshot["model_receipt_present"])
        self.assertFalse(snapshot["transport_receipt_present"])


if __name__ == "__main__":
    unittest.main()
