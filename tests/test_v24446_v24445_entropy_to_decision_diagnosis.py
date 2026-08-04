from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24446_v24445_entropy_to_decision as target  # noqa: E402


class V24446V24445EntropyToDecisionDiagnosisTests(unittest.TestCase):
    def test_diagnosis_separates_proved_and_unmeasured_causes(self) -> None:
        value = target.build_diagnosis(now=0)
        target.validate_diagnosis(value)
        evidence = value["entropy_to_decision_evidence"]
        self.assertGreater(evidence["narrative_epistemic_credit_total_nats"], 0)
        self.assertEqual(evidence["narrative_safe_change_count"], 0)
        self.assertEqual(evidence["narrative_decision_credit_total_nats"], 0)
        self.assertTrue(
            evidence["active_source_cap_alone_cannot_supply_known_baseline_minimum"]
        )
        self.assertFalse(evidence["third_source_alone_proven_sufficient"])
        self.assertFalse(value["claims"]["latency_root_cause_uniquely_identified"])

    def test_successor_preserves_thresholds_and_adds_only_one_fetch(self) -> None:
        value = target.build_diagnosis(now=0)
        order = value["successor_work_order"]
        self.assertTrue(order["preserve_safe_change_thresholds"])
        self.assertEqual(order["active_source_cap"], 3)
        self.assertEqual(order["additional_fetch_target_cap"], 1)
        self.assertEqual(order["additional_logical_query_or_search_batch"], 0)
        self.assertEqual(order["additional_model_request"], 0)
        self.assertTrue(order["publish_counts_only_threshold_failure_partition"])
        self.assertTrue(order["publish_content_free_child_and_post_child_stage_timings"])

    def test_only_successor_design_is_authorized(self) -> None:
        value = target.build_diagnosis(now=0)
        self.assertTrue(
            value["authorization"]["bounded_entropy_to_decision_successor_design"]
        )
        for name in (
            "external_probe_launch",
            "old_v24445_rerun",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_resealed_launch_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=0)
        altered = copy.deepcopy(value)
        altered["authorization"]["external_probe_launch"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_diagnosis(altered)


if __name__ == "__main__":
    unittest.main()
