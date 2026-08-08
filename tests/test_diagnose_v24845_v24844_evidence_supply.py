from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24844_atomic_table_header_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v24845_v24844_evidence_supply as target  # noqa: E402


class V24845EvidenceSupplyDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build(now=1786156000)

    def test_failure_partition_and_pair_transitions_reconcile(self) -> None:
        classes = {
            key: value["n"]
            for key, value in self.value["failure_class_aggregates"]["v24844"].items()
        }
        self.assertEqual(
            classes,
            {
                "entity_anchor_failure": 54,
                "evaluator_invalid": 11,
                "partial_quality": 142,
                "visible_schema_mismatch": 8,
                "whole_table_success": 5,
            },
        )
        pair = self.value["paired"]["v24840_to_v24844"]
        self.assertEqual(
            pair["exact_transitions"],
            {"both_exact": 4, "gained_exact": 1, "lost_exact": 3, "neither_exact": 212},
        )

    def test_internal_best_not_exceeded_and_causality_not_claimed(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertFalse(conclusions["v24844_exceeds_internal_v24800_exact_or_composite"])
        self.assertFalse(conclusions["v24844_atomic_header_causal_quality_gain_established"])
        self.assertFalse(conclusions["observational_bins_establish_causal_budget_gain"])
        self.assertFalse(conclusions["leaderboard_or_sota_established"])

    def test_evidence_supply_gradients_are_observed(self) -> None:
        fetch = self.value["v24844_observational_bins"]["fetch_failures"]
        projection = self.value["v24844_observational_bins"]["projected_chars"]
        self.assertGreater(fetch[0]["quality_composite"], fetch[3]["quality_composite"])
        self.assertGreater(projection[-1]["quality_composite"], projection[1]["quality_composite"])
        self.assertFalse(self.value["conclusions"]["atomic_header_dependency_actual_trigger_rate_observable"])

    def test_boundary_forbids_runtime_routing_and_task_content_emission(self) -> None:
        boundary = self.value["boundary"]
        self.assertFalse(boundary["failure_class_bin_or_historical_score_authorized_as_future_runtime_route"])
        self.assertFalse(boundary["network_model_search_fetch_or_evaluator_called"])
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.INSTANCE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))

    def test_resealed_tamper_fails_reproducibility(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["paired"]["v24840_to_v24844"]["exact_transitions"]["lost_exact"] = 2
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate(changed)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.45 publication has not been created")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value, target.validate(value))


if __name__ == "__main__":
    unittest.main()
