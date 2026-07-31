from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24223_sign_preserving_credit import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24223SignPreservingCreditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_sign_and_fail_closed_contracts(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        self.assertEqual(replay["valid_modulation_replay_count"], 3)
        for field in (
            "positive_negative_and_neutral_verifier_signs_covered",
            "entropy_increase_with_positive_terminal_contribution_covered",
            "entropy_decrease_cannot_reverse_negative_terminal_contribution",
            "zero_terminal_contribution_remains_zero",
            "invalid_intervention_rejected",
            "ood_intervention_rejected",
            "insufficient_replicates_rejected",
            "resealed_sign_flip_rejected",
        ):
            self.assertTrue(replay[field], field)
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
        self.assertTrue(value["claims"]["build_only_kernel_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["real_credit_estimate_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["training_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_forward_guard_and_scientific_limits_are_explicit(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertEqual(sum(guard["module_name_hit_count_by_file"].values()), 0)
        scope = self.value["scientific_scope"]
        self.assertTrue(scope["terminal_same_state_contribution_is_only_sign_source"])
        self.assertTrue(scope["entropy_provenance_and_cost_change_magnitude_only"])
        self.assertTrue(scope["entropy_increase_can_retain_positive_verified_credit"])
        self.assertFalse(
            scope["full_source_intervention_bundle_semantics_replayed_by_this_module"]
        )
        self.assertFalse(
            scope["caller_validity_attestations_independently_proven_by_this_module"]
        )
        self.assertFalse(scope["real_intervention_data_observed"])
        self.assertFalse(scope["gate2b_evaluated"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
