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

from deepwide_agent.v24436_narrative_title_anchor_projection import REASONS  # noqa: E402
from deepwide_agent.v24438_bounded_narrative_effect_runner import (  # noqa: E402
    build_envelope,
    run_v24438_task,
    validate_envelope as validate_memory_envelope,
)
from deepwide_agent.v24443_serialized_narrative_envelope import (  # noqa: E402
    normalize_serialized_envelope,
    validate_serialized_envelope,
    validate_serialized_observed_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24438_bounded_narrative_effect_runner import clients  # noqa: E402


class V24443SerializedNarrativeEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock)
        cls.outcome = run_v24438_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(cls.outcome)
        cls.wire = json.loads(
            json.dumps(cls.envelope, ensure_ascii=False, sort_keys=True)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_reproduces_v24442_memory_wire_validator_mismatch(self) -> None:
        validate_memory_envelope(self.envelope)
        with self.assertRaisesRegex(
            ValueError, "V2.44.36 narrative title projection identity drifted"
        ):
            validate_memory_envelope(self.wire)

    def test_normalization_is_json_value_and_seal_preserving(self) -> None:
        normalized = normalize_serialized_envelope(self.wire)
        self.assertEqual(
            json.dumps(self.wire, ensure_ascii=False, sort_keys=True),
            json.dumps(normalized, ensure_ascii=False, sort_keys=True),
        )
        self.assertEqual(
            normalized["envelope_payload_sha256"],
            self.wire["envelope_payload_sha256"],
        )
        result = normalized["narrative_title_result"]
        self.assertEqual(
            tuple(result["narrative_title_projection"]["reason_counts"]), REASONS
        )
        self.assertEqual(
            tuple(result["narrative_recovery_receipt"]["narrative_reason_counts"]),
            REASONS,
        )

    def test_wire_envelope_and_terminal_receipts_validate_together(self) -> None:
        value = validate_serialized_envelope(self.wire)
        self.assertEqual(value["envelope_payload_sha256"], self.envelope["envelope_payload_sha256"])
        validate_serialized_observed_bundle(
            self.wire,
            model_slot_receipt=json.loads(
                json.dumps(self.outcome.model_slot_receipt, sort_keys=True)
            ),
            transport_health=json.loads(
                json.dumps(self.outcome.transport_health, sort_keys=True)
            ),
            search_single_shot_receipt=json.loads(
                json.dumps(self.outcome.search_single_shot_receipt, sort_keys=True)
            ),
            expected_cap=2,
        )

    def test_reason_key_drift_still_fails_closed(self) -> None:
        for location, key in (
            ("narrative_title_projection", "reason_counts"),
            ("narrative_recovery_receipt", "narrative_reason_counts"),
        ):
            with self.subTest(location=location):
                altered = copy.deepcopy(self.wire)
                reasons = altered["narrative_title_result"][location][key]
                reasons.pop(next(iter(reasons)))
                with self.assertRaisesRegex(ValueError, "keys drifted"):
                    validate_serialized_envelope(altered)

    def test_non_order_tamper_is_not_repaired(self) -> None:
        altered = copy.deepcopy(self.wire)
        altered["narrative_title_result"]["candidate_prediction"] += "\n"
        with self.assertRaises(ValueError):
            validate_serialized_envelope(altered)


if __name__ == "__main__":
    unittest.main()
