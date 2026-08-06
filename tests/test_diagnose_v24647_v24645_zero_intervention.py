from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24647_v24645_zero_intervention as diagnosis
from deepwide_agent.v24645_ror_external_contract import ENTITY_GROUPS, payload_sha256
from deepwide_agent.v24645_ror_external_evaluator import GOLD, gold_rows


class ZeroInterventionDiagnosisTests(unittest.TestCase):
    def test_build_localizes_zero_intervention(self) -> None:
        value = diagnosis.build(now=0)
        self.assertEqual(value["quality"]["baseline_exact_table_successes"], 0)
        self.assertEqual(value["quality"]["candidate_exact_table_successes"], 0)
        self.assertEqual(
            value["baseline_fact_state_counts"]["ror"],
            {"correct": 12, "incorrect": 1, "unknown": 35},
        )
        self.assertEqual(value["baseline_fact_state_counts"]["country"], {"correct": 48})
        self.assertEqual(
            value["baseline_fact_state_counts"][
                "tasks_recoverable_if_all_ror_unknowns_were_safely_filled"
            ],
            11,
        )
        self.assertEqual(value["mechanism"]["structured_primary_identity_pair_count"], 3)
        self.assertEqual(value["mechanism"]["unknown_target_unique_pair_count"], 0)
        self.assertFalse(value["diagnosis"]["candidate_received_an_effective_treatment"])

    def test_claim_scope_and_authority_fail_closed(self) -> None:
        value = diagnosis.build(now=0)
        self.assertFalse(value["claim_scope"]["identity_gate_precision_measured"])
        self.assertFalse(value["claim_scope"]["unknown_fill_quality_measured"])
        self.assertFalse(value["claim_scope"]["deepwidebench_quality_measured"])
        self.assertFalse(value["claim_scope"]["entropy_or_credit_assignment_validated"])
        self.assertFalse(value["authorization"]["fresh_external_successor_launch"])
        self.assertFalse(value["authorization"]["dev64"])
        self.assertFalse(value["authorization"]["exact220"])
        unsigned = dict(value)
        seal = unsigned.pop("diagnosis_sha256")
        self.assertEqual(payload_sha256(unsigned), seal)

    def test_output_contains_no_private_entity_or_value_literal(self) -> None:
        value = diagnosis.build(now=0)
        serialized = json.dumps(value, ensure_ascii=False)
        for group in ENTITY_GROUPS:
            for entity in group:
                self.assertNotIn(entity, serialized)
        for row in gold_rows((ROOT / GOLD).read_text(encoding="utf-8")):
            self.assertNotIn(row["ROR ID"], serialized)
        self.assertNotIn("task_0000000000000000002464", serialized)

    def test_next_falsification_is_fresh_and_budget_matched(self) -> None:
        value = diagnosis.build(now=0)
        next_step = value["next_falsification"]
        self.assertEqual(next_step["population"], "fresh_and_literal_canonical_disjoint")
        self.assertTrue(next_step["same_total_model_query_fetch_budget"])
        self.assertFalse(next_step["same_population_resume_retry_or_selective_rerun"])
        self.assertFalse(next_step["unconditional_page_volume_increase"])
        self.assertTrue(next_step["separate_nonempty_correction_experiment_required"])

    def test_clean_guard_rejects_dirty_or_diverged_head(self) -> None:
        with patch.object(
            diagnosis.subprocess,
            "run",
            return_value=type("Completed", (), {"stdout": "dirty\n"})(),
        ):
            with self.assertRaisesRegex(RuntimeError, "clean HEAD"):
                diagnosis.clean()


if __name__ == "__main__":
    unittest.main()
