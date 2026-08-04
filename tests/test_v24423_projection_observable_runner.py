from __future__ import annotations

import copy
import json
import os
import re
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
from deepwide_agent.v24423_projection_observable_runner import (  # noqa: E402
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    build_envelope,
    run_and_persist_projection_observable_task,
    run_v24423_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24409_structured_uncertainty_runner import clients  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402


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


class V24423ProjectionObservableRunnerTests(unittest.TestCase):
    def make_directory(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def run_case(self):
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_v24423_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search, output

    def test_parent_behavior_is_unchanged_and_receipt_is_counts_only(self) -> None:
        outcome, model, search, _ = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        receipt = outcome.projection_observability_receipt
        recovery = outcome.result["structured_recovery_receipt"]
        self.assertEqual(receipt["page_count"], recovery["active_page_count"])
        self.assertEqual(
            receipt["structured_projection_count"],
            recovery["structured_projection_count"],
        )
        self.assertEqual(
            sum(receipt["reason_counts"].values()),
            receipt["page_target_pair_count"],
        )
        self.assertEqual(model.acquisitions, outcome.model_slot_receipt["acquisitions"])
        self.assertEqual(search.fetch_invocations, 3)
        encoded = json.dumps(receipt, sort_keys=True)
        for private in ("Alpha", "Beta", "2025", "https://"):
            self.assertNotIn(private, encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))

    def test_parent_or_observability_tamper_fails_closed(self) -> None:
        outcome, _, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        for field in ("parent", "reason"):
            with self.subTest(field=field):
                altered = copy.deepcopy(envelope)
                if field == "parent":
                    altered["parent_envelope"]["effect_equivalence_receipt"][
                        "model_remaining_seconds_after"
                    ] += 0.001
                    receipt = altered["parent_envelope"][
                        "effect_equivalence_receipt"
                    ]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                    parent = altered["parent_envelope"]
                    parent.pop("envelope_payload_sha256")
                    parent["envelope_payload_sha256"] = payload_sha256(parent)
                else:
                    reasons = altered["projection_observability_receipt"][
                        "reason_counts"
                    ]
                    reasons["structured_projection_emitted"] -= 1
                    reasons["exact_label_value_year_absent"] += 1
                    receipt = altered["projection_observability_receipt"]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_envelope(altered)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        with self.assertRaises(ValueError):
            run_v24423_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_success_persists_parent_terminal_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_and_persist_projection_observable_task(
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
        envelope = json.loads((output / RESULT_NAME).read_text(encoding="utf-8"))
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )

    def test_observability_failure_preserves_partial_effect_receipts(self) -> None:
        output = self.make_directory()
        clock = AdvancingClock()
        model, search = clients(output, clock)
        with patch(
            "deepwide_agent.v24423_projection_observable_runner.build_projection_observability",
            side_effect=RuntimeError("private detail"),
        ):
            with self.assertRaises(RuntimeError):
                run_and_persist_projection_observable_task(
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


if __name__ == "__main__":
    unittest.main()
