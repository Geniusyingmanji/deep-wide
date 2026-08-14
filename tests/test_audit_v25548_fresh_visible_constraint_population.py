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

from scripts import audit_v25548_fresh_visible_constraint_population as target  # noqa: E402


class V25548FreshVisibleConstraintPopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freshness = target._history_freshness()

    def test_parent_and_population_hash_barriers_are_exact(self) -> None:
        self.assertTrue(target._parent_barrier())
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)
        history = set(
            target.base._git(
                "rev-list", target.base._git("rev-parse", "HEAD")
            ).splitlines()
        )
        self.assertIn(target.POPULATION_COMMIT, history)

    def test_repository_tree_and_ancestry_freshness_are_zero(self) -> None:
        value = self.freshness
        self.assertEqual(value["identity_count"], 40)
        self.assertEqual(value["tree_exact_literal_match_count"], 0)
        self.assertEqual(
            value["ancestry_exact_literal_introduction_commit_count"], 0
        )

    def test_exact220_visible_overlap_is_zero_without_labels(self) -> None:
        value = target._exact220_overlap()
        self.assertEqual(value["fixed_visible_task_count"], 220)
        self.assertEqual(value["question_overlap_count"], 0)
        self.assertEqual(value["opaque_id_overlap_count"], 0)
        self.assertFalse(value["question_opaque_id_or_per_task_features_persisted"])

    def test_population_audit_authorizes_protocol_design_only(self) -> None:
        with mock.patch.object(
            target, "_history_freshness", return_value=copy.deepcopy(self.freshness)
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(
            value["visible_contract_reach"],
            {
                "task_count": 20,
                "active_constraint_tasks": 20,
                "date_format_tasks": 10,
                "numeric_scale_tasks": 10,
                "explicit_order_tasks": 20,
                "temporal_year_range_tasks": 0,
                "rank_slots_tasks": 0,
            },
        )
        authorization = value["authorization"]
        self.assertTrue(authorization["fresh_shared_parent_external_protocol_design"])
        self.assertFalse(authorization["external_forward"])
        self.assertFalse(authorization["postfreeze_truth_or_quality"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])

    def test_resealed_freshness_gate_credit_or_authority_tamper_fails(self) -> None:
        with mock.patch.object(
            target, "_history_freshness", return_value=copy.deepcopy(self.freshness)
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("freshness", "gate", "credit", "authority", "watcher", "git"):
            changed = copy.deepcopy(value)
            if kind == "freshness":
                changed["selection_freshness"]["tree_exact_literal_match_count"] = 1
            elif kind == "gate":
                changed["mechanism_gate"]["minimum_candidate_prediction_changed_tasks"] = 0
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            elif kind == "authority":
                changed["authorization"]["external_forward"] = True
            elif kind == "watcher":
                changed["protected_watchers"][0]["start_ticks"] += 1
            else:
                changed["git"]["clean"] = False
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
