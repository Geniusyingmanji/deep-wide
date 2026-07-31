from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit_v24224_credit_source_adapter import (
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24224CreditSourceAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_source_graph_and_fail_closed_contracts(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "valid_six_receipt_graph_replayed",
            "failed_branch_unit_loss_contribution_replayed",
            "missing_receipt_rejected",
            "resealed_freeze_tamper_rejected",
            "resealed_provenance_tamper_rejected",
            "resealed_sign_flip_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["signed_contribution_vector"], [0.4, -0.2, 0.1])
        self.assertFalse(
            replay["semantic_or_distributional_ood_independently_assessed"]
        )
        self.assertFalse(
            replay["evaluator_live_provenance_independently_replayed"]
        )
        self.assertFalse(replay["synthetic_benchmark_rows_or_content_read"])

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

    def test_audit_is_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_source_adapter_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["real_credit_estimate_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_forward_guard_and_scientific_limits_are_explicit(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertEqual(sum(guard["module_name_hit_count_by_file"].values()), 0)
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["terminal_same_state_contribution_is_only_sign_source"])
        self.assertTrue(scope["prediction_freeze_artifact_validated"])
        self.assertTrue(
            scope["post_freeze_evaluator_provenance_binding_validated"]
        )
        self.assertFalse(scope["evaluator_live_provenance_independently_replayed"])
        self.assertFalse(
            scope["semantic_or_distributional_ood_independently_assessed"]
        )
        self.assertFalse(scope["real_intervention_data_observed"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
