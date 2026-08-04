from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (  # noqa: E402
    ValidatedSerializedThirdSourceEnvelope,
    normalize_serialized_envelope,
    validate_serialized_envelope,
    validate_serialized_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


class V24448SerializedThirdSourceEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock, third=True)
        outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(outcome)
        cls.outcome = outcome
        cls.wire = json.loads(
            json.dumps(cls.envelope, ensure_ascii=False, sort_keys=True)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_sorted_json_round_trip_validates_without_value_change(self) -> None:
        normalized = normalize_serialized_envelope(self.wire)
        self.assertEqual(
            json.dumps(self.wire, sort_keys=True, separators=(",", ":")),
            json.dumps(normalized, sort_keys=True, separators=(",", ":")),
        )
        capability = validate_serialized_envelope(self.wire)
        self.assertIsInstance(capability, ValidatedSerializedThirdSourceEnvelope)
        self.assertEqual(
            capability.snapshot()["envelope_payload_sha256"],
            self.envelope["envelope_payload_sha256"],
        )
        self.assertFalse(capability.observed_bundle_validated())
        with self.assertRaises(ValueError):
            capability.counts_only_receipts()

    def test_observed_bundle_capability_exposes_only_content_free_receipts(self) -> None:
        capability = validate_serialized_observed_bundle(
            self.wire,
            model_slot_receipt=self.outcome.model_slot_receipt,
            transport_health=self.outcome.transport_health,
            search_single_shot_receipt=self.outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        self.assertTrue(capability.observed_bundle_validated())
        self.assertEqual(
            set(capability.counts_only_receipts()),
            {"third_source_recovery_receipt", "effect_delta_receipt"},
        )

    def test_capability_cannot_be_constructed_from_unvalidated_mapping(self) -> None:
        with self.assertRaises(TypeError):
            ValidatedSerializedThirdSourceEnvelope(self.wire)

    def test_reason_partition_or_private_page_tamper_fails_closed(self) -> None:
        for field in ("partition", "page"):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.wire)
                result = altered["third_source_result"]
                if field == "partition":
                    receipt = result["third_source_recovery_receipt"]
                    receipt["threshold_failure_partition"][
                        "insufficient_support_count"
                    ] += 1
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                    result.pop("result_sha256")
                    result["result_sha256"] = payload_sha256(result)
                else:
                    result["third_source_private_state"]["third_fetch_batches"][0][
                        "results"
                    ][0]["raw_content"] += " tamper"
                    result.pop("result_sha256")
                    result["result_sha256"] = payload_sha256(result)
                altered.pop("envelope_payload_sha256")
                altered["envelope_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_serialized_envelope(altered)


if __name__ == "__main__":
    unittest.main()
