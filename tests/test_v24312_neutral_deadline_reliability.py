from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24312_neutral_deadline_reliability as target  # noqa: E402


class NeutralDeadlineReliabilityTests(unittest.TestCase):
    def test_content_free_diagnosis_matches_four_frozen_failures(self) -> None:
        value = target.build_diagnosis(ROOT, now=1)
        target.validate_diagnosis(ROOT, value)
        self.assertEqual(value["non_success_task_count"], 4)
        self.assertEqual(
            sum(
                item["parent_taxonomy"] == "hard_deadline_timeout"
                for item in value["failures"]
            ),
            3,
        )
        self.assertFalse(
            value["mapping_gold_category_question_type_split_evaluator_score_read"]
        )

    def test_protocol_is_benchmark_external_and_grants_no_launch(self) -> None:
        # The source manifest is intentionally checked from current bytes; the
        # production preregistration later seals those bytes create-exclusively.
        diagnosis = target.build_diagnosis(ROOT, now=1)
        with tempfile.TemporaryDirectory(dir=ROOT / "results") as temporary:
            path = Path(temporary) / target.DIAGNOSIS.name
            path.write_text(json.dumps(diagnosis), encoding="utf-8")
            original = target.DIAGNOSIS
            target.DIAGNOSIS = path.relative_to(ROOT)
            try:
                value = target.build_protocol(ROOT, now=1)
                target.validate_protocol(ROOT, value)
            finally:
                target.DIAGNOSIS = original
        self.assertEqual(value["external_network_model_search_fetch_or_evaluator_calls"], 0)
        self.assertFalse(value["authorization"]["fresh_paired_dev64_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_real_subprocess_probe_has_fixed_denominator_and_total_receipts(self) -> None:
        value = target.execute_probe(ROOT)
        target.validate_projection(value)
        self.assertEqual(value["terminal_cases"], len(target.MODES))
        self.assertEqual(value["parent_receipts_created"], len(target.MODES))
        self.assertEqual(value["child_terminal_receipts_created"], len(target.MODES))
        self.assertFalse(any(value["external_effect_ledger"].values()))
        self.assertEqual(value["fourth_model_effects"], 0)

    def test_resealed_extra_case_field_fails_closed(self) -> None:
        value = target.execute_probe(ROOT)
        altered = copy.deepcopy(value["cases"]["immediate_success"])
        altered["question"] = "forbidden"
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(ValueError, "envelope drifted"):
            target.validate_envelope(altered)


if __name__ == "__main__":
    unittest.main()
