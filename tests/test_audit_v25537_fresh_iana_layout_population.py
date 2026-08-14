from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25537_fresh_iana_layout_population as target  # noqa: E402


class V25537FreshIanaLayoutPopulationAuditTests(unittest.TestCase):
    def test_build_selection_hashes_and_history_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(target._selection_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )
        history = set(target.base._git("rev-list", "HEAD").splitlines())
        self.assertIn(target.POPULATION_COMMIT, history)

    def test_all_historical_task_populations_are_closed_and_disjoint(self) -> None:
        manifest, historical = target._historical_task_closure()
        current = target.population.task_vector()
        self.assertEqual(len(manifest), 25)
        self.assertEqual(len(historical), 508)
        self.assertEqual(len({row["question"] for row in historical}), 508)
        self.assertEqual(len({row["opaque_id"] for row in historical}), 508)
        self.assertFalse(
            {row["question"] for row in current}
            & {row["question"] for row in historical}
        )
        self.assertFalse(
            {row["opaque_id"] for row in current}
            & {row["opaque_id"] for row in historical}
        )

    def test_population_audit_passes_without_external_effect(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["selection"]["row_identity_count"], 40)
        self.assertEqual(value["selection"]["consumed_identity_count"], 260)
        self.assertEqual(
            value["selection"]["consumed_identity_overlap_count"], 0
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_atomic_layout_gate_is_frozen_before_forward(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        gate = value["mechanism_gate"]
        self.assertEqual(gate["minimum_iana_layout_complete_page_tasks"], 2)
        self.assertEqual(gate["minimum_raw_field_surface_tasks"], 4)
        self.assertEqual(gate["minimum_applied_coordinate_count_total"], 4)
        self.assertEqual(gate["minimum_treatment_changed_tasks"], 2)
        self.assertEqual(
            gate["minimum_treatment_changed_coordinate_count_total"], 4
        )
        self.assertEqual(gate["candidate_additional_fetches_beyond_parent"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_resealed_overlap_closure_launch_or_credit_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("overlap", "closure", "hash", "watcher", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "overlap":
                changed["selection"]["consumed_identity_overlap_count"] = 1
            elif kind == "closure":
                changed["historical_task_closure"]["task_count"] = 507
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.BUILD_AUDIT)] = "0" * 64
            elif kind == "watcher":
                changed["protected_watchers"][0]["pid"] += 1
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
