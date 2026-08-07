from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24835_v24831_v24834_evidence_budget as diagnosis  # noqa: E402


class V24835EvidenceBudgetDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = diagnosis.build(now=1_786_140_000)

    def test_exact220_reconciles_and_quality_regresses(self) -> None:
        self.assertEqual(self.report["overall"]["control"]["n"], 220)
        self.assertEqual(self.report["overall"]["candidate"]["n"], 220)
        self.assertEqual(self.report["overall"]["delta"]["whole_table_success_delta"], 2)
        self.assertLess(
            self.report["overall"]["delta"]["metrics"]["quality_composite"], 0
        )

    def test_more_retrieval_and_context_did_not_prove_quality_gain(self) -> None:
        delta = self.report["overall"]["delta"]["mechanism"]
        for name in (
            "queries_executed", "fetches_attempted", "usable_pages",
            "unique_hosts", "content_chars", "projected_chars",
            "model_input_tokens", "search_input_tokens",
        ):
            self.assertGreater(delta[name], 0, name)
        self.assertFalse(
            self.report["conclusions"]["more_retrieval_is_universally_better"]
        )

    def test_route_partition_and_bootstrap_cover_all_tasks(self) -> None:
        self.assertEqual(sum(self.report["route_transitions"].values()), 220)
        self.assertEqual(
            sum(self.report["paired_composite_bootstrap"]["direction_counts"].values()),
            220,
        )

    def test_report_is_aggregate_only_and_label_blind(self) -> None:
        encoded = json.dumps(self.report, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("| Result |", encoded)
        boundary = self.report["boundary"]
        self.assertFalse(boundary["task_result_prediction_field_used"])
        self.assertFalse(boundary["mapping_answer_category_question_type_split_resource_opened"])
        self.assertFalse(boundary["historical_score_stratum_or_correlation_authorized_as_future_runtime_input"])

    def test_successor_requires_fresh_shared_prefix_external_gate(self) -> None:
        work = self.report["next_work"]
        self.assertEqual(
            work["candidate"], "shared_prefix_information_bottleneck_evidence_projection"
        )
        self.assertFalse(work["public_exact220_authorized_after_this_diagnosis"])
        self.assertIn(
            "same plan query search fetch and raw page bytes",
            work["required_external_gate_controls"],
        )

    def test_resealed_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.report)
        altered["overall"]["delta"]["whole_table_success_delta"] += 1
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            diagnosis.validate(altered)


if __name__ == "__main__":
    unittest.main()
