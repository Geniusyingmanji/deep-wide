from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24413_effect_equivalence import (  # noqa: E402
    compare_effect_snapshots,
    validate_effect_equivalence_receipt,
)
from test_v24412_receipt_snapshot_diagnosis import (  # noqa: E402
    AdvancingClock,
    clients,
)


def snapshots():
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    output = Path(temporary.name)
    clock = AdvancingClock()
    model, search = clients(output, clock)
    before = (
        model.receipt(),
        search.transport_health(),
        search.single_shot_receipt(),
    )
    after = (
        model.receipt(),
        search.transport_health(),
        search.single_shot_receipt(),
    )
    return temporary, before, after


def reseal_model(value: dict) -> dict:
    value = copy.deepcopy(value)
    value.pop("receipt_payload_sha256", None)
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


class V24413EffectEquivalenceTests(unittest.TestCase):
    def test_advancing_clock_is_equivalent_when_effects_are_unchanged(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        receipt = compare_effect_snapshots(
            model_before=before[0],
            model_after=after[0],
            transport_before=before[1],
            transport_after=after[1],
            search_before=before[2],
            search_after=after[2],
            expected_model_cap=2,
        )
        validate_effect_equivalence_receipt(receipt)
        self.assertGreater(
            receipt["model_remaining_seconds_before"],
            receipt["model_remaining_seconds_after"],
        )
        self.assertFalse(receipt["external_effect_detected"])

    def test_model_effect_counter_change_is_rejected(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        drifted = copy.deepcopy(after[0])
        drifted["acquisitions"] += 1
        drifted["slot_acquisition_counts"][0] += 1
        drifted = reseal_model(drifted)
        with self.assertRaisesRegex(ValueError, "not effect-equivalent"):
            compare_effect_snapshots(
                model_before=before[0],
                model_after=drifted,
                transport_before=before[1],
                transport_after=after[1],
                search_before=before[2],
                search_after=after[2],
                expected_model_cap=2,
            )

    def test_transport_effect_counter_change_is_rejected(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        drifted = copy.deepcopy(after[1])
        drifted["hosted_search_attempts"] += 1
        with self.assertRaisesRegex(ValueError, "not effect-equivalent"):
            compare_effect_snapshots(
                model_before=before[0],
                model_after=after[0],
                transport_before=before[1],
                transport_after=drifted,
                search_before=before[2],
                search_after=after[2],
                expected_model_cap=2,
            )

    def test_search_shape_change_is_rejected(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        drifted = copy.deepcopy(after[2])
        drifted["multi_query_chunks"] += 1
        with self.assertRaisesRegex(ValueError, "not effect-equivalent"):
            compare_effect_snapshots(
                model_before=before[0],
                model_after=after[0],
                transport_before=before[1],
                transport_after=after[1],
                search_before=before[2],
                search_after=drifted,
                expected_model_cap=2,
            )

    def test_remaining_time_increase_is_rejected(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        drifted = copy.deepcopy(after[0])
        drifted["remaining_seconds_at_receipt"] = (
            before[0]["remaining_seconds_at_receipt"] + 1.0
        )
        drifted = reseal_model(drifted)
        with self.assertRaisesRegex(ValueError, "not effect-equivalent"):
            compare_effect_snapshots(
                model_before=before[0],
                model_after=drifted,
                transport_before=before[1],
                transport_after=after[1],
                search_before=before[2],
                search_after=after[2],
                expected_model_cap=2,
            )

    def test_deadline_state_may_only_move_false_to_true(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        before_model = copy.deepcopy(before[0])
        before_model["deadline_exhausted"] = True
        before_model = reseal_model(before_model)
        after_model = copy.deepcopy(after[0])
        after_model["deadline_exhausted"] = False
        after_model = reseal_model(after_model)
        with self.assertRaisesRegex(ValueError, "not effect-equivalent"):
            compare_effect_snapshots(
                model_before=before_model,
                model_after=after_model,
                transport_before=before[1],
                transport_after=after[1],
                search_before=before[2],
                search_after=after[2],
                expected_model_cap=2,
            )

    def test_receipt_tamper_and_label_blind_claim_fail_closed(self) -> None:
        temporary, before, after = snapshots()
        self.addCleanup(temporary.cleanup)
        receipt = compare_effect_snapshots(
            model_before=before[0],
            model_after=after[0],
            transport_before=before[1],
            transport_after=after[1],
            search_before=before[2],
            search_after=after[2],
            expected_model_cap=2,
        )
        altered = copy.deepcopy(receipt)
        altered[
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ] = True
        altered.pop("receipt_sha256")
        altered["receipt_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_effect_equivalence_receipt(altered)


if __name__ == "__main__":
    unittest.main()
