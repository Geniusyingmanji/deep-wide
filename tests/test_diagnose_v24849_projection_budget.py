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

from deepwide_agent import v24848_atomic_table_header_30k_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v24849_v24844_v24848_projection_budget as target  # noqa: E402


class V24849ProjectionBudgetDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build(now=1786159500)

    def test_exact220_and_metric_reconciliation(self) -> None:
        value = self.value
        self.assertEqual(value["overall"]["v24844"]["n"], 220)
        self.assertEqual(value["overall"]["v24848"]["n"], 220)
        self.assertEqual(
            sum(value["overall"]["paired"]["exact_transitions"].values()), 220
        )
        self.assertAlmostEqual(
            value["overall"]["v24848"]["metrics"]["quality_composite"],
            0.43664299038692556,
        )

    def test_receipts_reconcile_and_closure_was_inactive(self) -> None:
        totals = self.value["mechanism"]["v24848_projection_receipt_totals"]
        self.assertEqual(totals["valid_receipts"], 220)
        self.assertEqual(totals["rendered_characters"], 4_494_390)
        self.assertEqual(totals["missed_supported_visible_requirements"], 0)
        self.assertEqual(totals["selected_table_continuations"], 0)
        self.assertEqual(totals["table_header_dependency_additions"], 0)
        self.assertEqual(totals["orphan_table_continuations"], 0)

    def test_no_go_and_causality_boundaries(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertFalse(conclusions["v24848_exceeds_v24844_exact_or_composite"])
        self.assertFalse(
            conclusions[
                "v24847_external_shared_prefix_gain_transferred_to_deepwidebench"
            ]
        )
        self.assertFalse(
            conclusions["independent_fullset_rollouts_identify_projection_cap_causality"]
        )
        self.assertFalse(
            conclusions["v24848_naturally_tested_atomic_table_continuation_closure"]
        )
        self.assertFalse(conclusions["entropy_or_information_gain_credit_validated"])

    def test_output_is_aggregate_only_and_future_label_blind(self) -> None:
        boundary = self.value["boundary"]
        self.assertFalse(
            boundary[
                "historical_metric_bin_or_evaluator_outcome_authorized_as_future_runtime_route"
            ]
        )
        self.assertFalse(boundary["network_model_search_fetch_or_evaluator_called"])
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.INSTANCE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))

    def test_tamper_fails_even_if_resealed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["conclusions"][
            "v24847_external_shared_prefix_gain_transferred_to_deepwidebench"
        ] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate(changed, rebuild=False)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.49 publication has not been created")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value, target.validate(value))


if __name__ == "__main__":
    unittest.main()
