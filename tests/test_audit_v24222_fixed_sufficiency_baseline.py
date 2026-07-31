from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24222_fixed_sufficiency_baseline import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24222FixedSufficiencyBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_contract_replay_covers_decisions_and_fail_closed_edges(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        self.assertEqual(replay["decision_replay_count"], 4)
        self.assertEqual(
            replay["decision_kinds_observed"],
            ["abstain_budget_exhausted", "answer_ready", "continue"],
        )
        for field in (
            "criteria_frozen_before_first_action",
            "post_action_catalog_construction_rejected",
            "contradicted_criterion_prioritized",
            "budget_exhaustion_is_not_task_success",
            "answer_ready_is_not_task_success",
            "support_contradiction_conflict_rejected",
            "nested_privileged_metadata_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["synthetic_content_or_benchmark_rows_read"])

    def test_static_audit_rejects_io_network_and_dynamic_code(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('X')\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_is_build_only_and_claims_only_implementation(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["baseline_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["baseline_implementation_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_scientific_scope_discloses_unproven_semantics_and_chronology(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["fixed_evidence_sufficiency_termination_implemented"])
        self.assertTrue(scope["catalog_requires_empty_supplied_presearch_action_trace"])
        self.assertFalse(scope["criterion_semantic_quality_validated"])
        self.assertFalse(
            scope["criterion_derivation_from_visible_input_projection_proven"]
        )
        self.assertFalse(scope["chronology_beyond_supplied_trace_attestation_proven"])
        self.assertFalse(scope["active_evidence_snapshot_completeness_proven"])
        self.assertFalse(scope["source_independence_estimated_or_claimed"])
        self.assertFalse(scope["four_layer_open_world_risk_implemented"])
        self.assertFalse(scope["entropy_information_gain_or_voc_implemented"])
        self.assertFalse(scope["quality_cost_or_benchmark_effect_observed"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
