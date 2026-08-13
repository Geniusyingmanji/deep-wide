from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_v25422_fresh_rfc_list_atomic_population as target  # noqa: E402


class V25422FreshRfcListAtomicPopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_candidate_order_and_first_zero_selection_are_fixed(self) -> None:
        self.assertEqual(
            self.value["candidate_interval_order"],
            ["RFC 9480-9559", "RFC 9560-9639", "RFC 9640-9719", "RFC 9720-9799"],
        )
        self.assertEqual(
            self.value["candidate_interval_aggregate_counts"], target.EXPECTED_COUNTS
        )
        self.assertEqual(
            self.value["selected_first_zero_collision_interval"], "RFC 9720-9799"
        )

    def test_population_vectors_and_denominators_are_bound(self) -> None:
        self.assertEqual(self.value["task_count"], 20)
        self.assertEqual(self.value["identity_count"], 80)
        self.assertEqual(
            self.value["identity_vector_sha256"],
            target.population.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            self.value["group_vector_sha256"],
            target.population.EXPECTED_GROUP_VECTOR_SHA256,
        )

    def test_audit_authorizes_only_protocol_design(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["fresh_list_atomic_gate_protocol_design"])
        self.assertFalse(authorization["candidate_page_or_endpoint_preflight"])
        self.assertFalse(
            authorization["network_model_search_fetch_external_forward_or_evaluator"]
        )
        self.assertFalse(
            authorization["deepwidebench_forward_evaluator_leaderboard_or_sota"]
        )

    def test_resealed_tamper_fails(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["selected_first_zero_collision_interval"] = "RFC 9640-9719"
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.population.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
