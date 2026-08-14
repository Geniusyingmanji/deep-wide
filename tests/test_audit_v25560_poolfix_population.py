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

from scripts import audit_v25560_poolfix_population as target  # noqa: E402


class V25560PoolfixPopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freshness = target._history_freshness()

    def test_fixed_hashes_commits_and_real_constructor_smoke(self) -> None:
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)
        history = set(target.base._git("rev-list", "HEAD").splitlines())
        self.assertIn(target.IMPLEMENTATION_COMMIT, history)
        self.assertIn(target.POOL_COMMIT, history)
        smoke = target._constructor_smoke()
        self.assertTrue(smoke["constructed"])
        self.assertEqual(smoke["pool_id"], target.pool.MODEL_POOL_ID)

    def test_tree_ancestry_fixed220_and_consumed_overlap_zero(self) -> None:
        self.assertEqual(self.freshness["tree_exact_literal_match_line_count"], 0)
        self.assertEqual(self.freshness["ancestry_patch_exact_literal_identity_hit_count"], 0)
        overlap = target._overlap()
        for name, value in overlap.items():
            if name.endswith("_count"):
                self.assertEqual(value, 0)

    def test_date_order_reach_exact_twenty_scale_zero(self) -> None:
        self.assertEqual(
            target._contract_reach(),
            {
                "task_count": 20, "active_constraint_tasks": 20,
                "date_format_tasks": 20, "numeric_scale_tasks": 0,
                "explicit_order_tasks": 20, "temporal_year_range_tasks": 0,
                "rank_slots_tasks": 0,
            },
        )

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with (
            mock.patch.object(target, "_history_freshness", return_value=copy.deepcopy(self.freshness)),
            mock.patch.object(target, "_tests", return_value={"expected": 9, "observed": 9, "passed": True, "suites": []}),
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["fresh_poolfixed_external_protocol_design"])
        self.assertFalse(value["authorization"]["external_forward"])

    def test_resealed_pool_freshness_overlap_credit_or_authority_tamper_fails(self) -> None:
        with (
            mock.patch.object(target, "_history_freshness", return_value=copy.deepcopy(self.freshness)),
            mock.patch.object(target, "_tests", return_value={"expected": 9, "observed": 9, "passed": True, "suites": []}),
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("pool", "freshness", "overlap", "credit", "authority"):
            changed = copy.deepcopy(value)
            if kind == "pool":
                changed["constructor_smoke"]["pool_id"] = "bad"
            elif kind == "freshness":
                changed["selection_freshness"]["tree_exact_literal_match_line_count"] = 1
            elif kind == "overlap":
                changed["overlap"]["v25553_consumed_identity_overlap_count"] = 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["external_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate(changed)


if __name__ == "__main__":
    unittest.main()
