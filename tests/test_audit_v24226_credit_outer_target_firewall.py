from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24226_credit_outer_target_firewall import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24226CreditOuterTargetFirewallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_independence_and_self_target_rejection(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "valid_independent_outer_target_pair_replayed",
            "same_frozen_manifest_and_semantic_bundle_reused",
            "inner_outer_arm_graph_hashes_disjoint",
            "equal_numeric_contribution_with_independent_artifacts_accepted",
            "same_source_graph_as_outer_target_rejected",
            "fit_calibration_audit_cluster_overlap_rejected",
            "prediction_builder_signature_excludes_outer_target",
            "diagnostic_aggregate_cannot_authorize_gate2b_pass",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["synthetic_benchmark_rows_or_content_read"])

    def test_static_audit_rejects_io_network_process_and_dynamic_code(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('X')\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_preserves_historical_gate_as_nonformal_regression(self) -> None:
        disposition = self.value["historical_gate_disposition"]
        self.assertTrue(
            disposition[
                "historical_synthetic_same_target_pass_preserved_for_regression_only"
            ]
        )
        self.assertFalse(
            disposition["historical_gate_authorizes_formal_gate2b_claim_after_v24226"]
        )
        self.assertTrue(
            disposition["formal_future_gate_requires_independent_outer_target_pairs"]
        )
        self.assertTrue(
            all(
                count == 0
                for count in disposition[
                    "v24226_module_name_hit_count_by_file"
                ].values()
            )
        )

    def test_audit_is_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_firewall_available"])
        self.assertFalse(value["claims"]["formal_gate2b_evaluator_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_scientific_scope_discloses_remaining_evidence_gaps(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["outcome_anchored_credit_self_target_confirmation_identified"])
        self.assertTrue(scope["same_source_contribution_as_outer_target_rejected"])
        self.assertFalse(scope["wall_clock_creation_order_independently_proven"])
        self.assertFalse(scope["semantic_or_distributional_ood_independently_assessed"])
        self.assertFalse(scope["real_independent_outer_target_data_observed"])
        self.assertFalse(scope["cluster_bootstrap_or_stress_family_minima_evaluated"])
        self.assertFalse(scope["gate2b_evaluated"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
