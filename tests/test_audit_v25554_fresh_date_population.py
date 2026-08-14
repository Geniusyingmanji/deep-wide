from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25554_fresh_date_population as target  # noqa: E402


class V25554FreshDatePopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freshness = target._history_freshness()

    def test_fixed_implementation_hashes_and_commit_barrier(self) -> None:
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)
        self.assertIn(
            target.IMPLEMENTATION_COMMIT,
            set(target.base._git("rev-list", "HEAD").splitlines()),
        )

    def test_repository_tree_and_ancestry_patch_freshness_are_zero(self) -> None:
        value = self.freshness
        self.assertEqual(value["identity_count"], 40)
        self.assertEqual(value["tree_exact_literal_match_line_count"], 0)
        self.assertEqual(value["ancestry_patch_exact_literal_identity_hit_count"], 0)

    def test_exact220_visible_overlap_is_zero_without_labels(self) -> None:
        value = target._exact220_overlap()
        self.assertEqual(value["fixed_visible_task_count"], 220)
        self.assertEqual(value["question_overlap_count"], 0)
        self.assertEqual(value["opaque_id_overlap_count"], 0)
        self.assertFalse(value["question_opaque_id_or_per_task_features_persisted"])

    def test_contract_reach_is_exactly_date_and_order_for_all_twenty(self) -> None:
        self.assertEqual(
            target._contract_reach(),
            {
                "task_count": 20,
                "active_constraint_tasks": 20,
                "date_format_tasks": 20,
                "numeric_scale_tasks": 0,
                "explicit_order_tasks": 20,
                "temporal_year_range_tasks": 0,
                "rank_slots_tasks": 0,
            },
        )

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with (
            mock.patch.object(
                target, "_history_freshness", return_value=copy.deepcopy(self.freshness)
            ),
            mock.patch.object(
                target,
                "_tests",
                return_value={
                    "expected": 12,
                    "observed": 12,
                    "passed": True,
                    "suites": [],
                },
            ),
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["authorization"]["fresh_shared_parent_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["postfreeze_truth_or_quality"])
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])

    def test_resealed_freshness_gate_truth_credit_or_authority_tamper_fails(self) -> None:
        with (
            mock.patch.object(
                target, "_history_freshness", return_value=copy.deepcopy(self.freshness)
            ),
            mock.patch.object(
                target,
                "_tests",
                return_value={
                    "expected": 12,
                    "observed": 12,
                    "passed": True,
                    "suites": [],
                },
            ),
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("freshness", "gate", "truth", "credit", "authority", "watcher"):
            changed = copy.deepcopy(value)
            if kind == "freshness":
                changed["selection_freshness"][
                    "tree_exact_literal_match_line_count"
                ] = 1
            elif kind == "gate":
                changed["mechanism_gate"]["minimum_candidate_prediction_changed_tasks"] = 0
            elif kind == "truth":
                changed["truth_policy"][
                    "official_identity_bound_no_stable_release_is_valid_unknown"
                ] = False
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "authority":
                changed["authorization"]["external_forward"] = True
            else:
                changed["protected_watchers"][0]["start_ticks"] += 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
