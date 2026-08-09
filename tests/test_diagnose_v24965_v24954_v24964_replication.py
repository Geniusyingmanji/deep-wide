from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24965_v24954_v24964_replication as diagnosis  # noqa: E402


def row(*, score: float, entity: float, row_f1: float, item: float, column: float, valid: bool = True):
    return {
        "evaluator_valid": valid,
        "metrics": {
            "score": score,
            "entity_acc": entity,
            "f1_by_row": row_f1,
            "f1_by_item": item,
            "column_f1": column,
        },
    }


class V24965ReplicationDiagnosisTests(unittest.TestCase):
    def test_paired_quality_counts_wins_ties_and_losses(self) -> None:
        left = [
            row(score=0, entity=0.2, row_f1=0.2, item=0.2, column=0.2),
            row(score=0, entity=0.5, row_f1=0.5, item=0.5, column=0.5),
            row(score=0, entity=0.9, row_f1=0.9, item=0.9, column=0.9),
        ]
        right = [
            row(score=0, entity=0.4, row_f1=0.4, item=0.4, column=0.4),
            row(score=0, entity=0.5, row_f1=0.5, item=0.5, column=0.5),
            row(score=0, entity=0.7, row_f1=0.7, item=0.7, column=0.7),
        ]
        value = diagnosis.paired_quality(left, right)
        self.assertEqual(value["quality_composite"]["candidate_wins"], 1)
        self.assertEqual(value["quality_composite"]["ties"], 1)
        self.assertEqual(value["quality_composite"]["candidate_losses"], 1)
        self.assertAlmostEqual(value["quality_composite"]["mean_delta"], 0.0)

    def test_exact_transition_partition(self) -> None:
        left = [row(score=value, entity=0, row_f1=0, item=0, column=0) for value in (1, 1, 0, 0)]
        right = [row(score=value, entity=0, row_f1=0, item=0, column=0) for value in (1, 0, 1, 0)]
        self.assertEqual(
            diagnosis.exact_transitions(left, right),
            {
                "both_exact": 1,
                "candidate_only_exact": 1,
                "control_only_exact": 1,
                "neither_exact": 1,
            },
        )

    def test_validity_transition_partition(self) -> None:
        left = [row(score=0, entity=0, row_f1=0, item=0, column=0, valid=value) for value in (True, True, False, False)]
        right = [row(score=0, entity=0, row_f1=0, item=0, column=0, valid=value) for value in (True, False, True, False)]
        self.assertEqual(sum(diagnosis.validity_transitions(left, right).values()), 4)

    def test_empty_or_unpaired_vectors_rejected(self) -> None:
        with self.assertRaises(ValueError):
            diagnosis.paired_quality([], [])
        with self.assertRaises(ValueError):
            diagnosis.paired_quality(
                [row(score=0, entity=0, row_f1=0, item=0, column=0)], []
            )

    def test_current_result_is_aggregate_and_valid(self) -> None:
        value = diagnosis.build_result(now=1)
        self.assertEqual(value["paired_task_count"], 220)
        self.assertEqual(sum(value["exact_transitions"].values()), 220)
        self.assertEqual(sum(value["validity_transitions"].values()), 220)
        self.assertFalse(
            value["diagnosis"]["algorithmic_gain_attributable_to_partial_signature"]
        )
        self.assertFalse(value["diagnosis"]["public_exact220_successor_authorized"])

    def test_current_mechanism_receipts_are_complete(self) -> None:
        value = diagnosis.build_result(now=1)
        self.assertEqual(value["mechanism_exposure"]["v24954"]["valid_receipts"], 220)
        self.assertEqual(value["mechanism_exposure"]["v24964"]["valid_receipts"], 220)

    def test_audit_rejects_per_task_content_key(self) -> None:
        value = diagnosis.build_result(now=1)
        tampered = copy.deepcopy(value)
        tampered["question"] = "forbidden"
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = diagnosis.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            diagnosis.build_audit(tampered, now=1)

    def test_result_seal_rejects_tamper(self) -> None:
        value = diagnosis.build_result(now=1)
        value["paired_task_count"] = 219
        with self.assertRaises(RuntimeError):
            diagnosis.validate_result(value)

    def test_source_policy_grants_no_public_launch(self) -> None:
        value = diagnosis.build_result(now=1)
        self.assertFalse(
            value["authorization"]["public_exact220_or_other_benchmark_launch"]
        )
        self.assertFalse(
            value["source_policy"][
                "diagnosis_used_for_same_run_forward_routing_or_prediction_selection"
            ]
        )


if __name__ == "__main__":
    unittest.main()
