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

from scripts import (  # noqa: E402
    audit_v25578_fresh_canonical_totality_population as target,
)


class V25578FreshCanonicalTotalityPopulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freshness = target._history_freshness()

    def test_fixed_hashes_commit_and_population_vectors(self) -> None:
        for path, expected in target.FIXED_HASHES.items():
            self.assertEqual(target.base.sha256(path), expected)
        history = set(target.base._git("rev-list", "HEAD").splitlines())
        self.assertIn(target.IMPLEMENTATION_COMMIT, history)
        self.assertEqual(len(target.population.identity_vector()), 40)
        self.assertEqual(len(target.population.task_vector()), 20)

    def test_tree_ancestry_fixed220_and_all_population_overlap_zero(self) -> None:
        self.assertEqual(self.freshness["tree_exact_literal_match_line_count"], 0)
        self.assertEqual(
            self.freshness["ancestry_patch_exact_literal_identity_hit_count"],
            0,
        )
        overlap = target._overlap()
        self.assertEqual(overlap["fixed220_question_overlap_count"], 0)
        self.assertEqual(overlap["fixed220_opaque_overlap_count"], 0)
        self.assertGreaterEqual(overlap["historical_population_module_count"], 22)
        for value in overlap["historical_population_overlaps"].values():
            self.assertEqual(value["identity_overlap_count"], 0)
            self.assertEqual(value["question_overlap_count"], 0)

    def test_exposure_reach_is_exact_ten_ten_without_constraint(self) -> None:
        self.assertEqual(
            target._exposure_reach(),
            {
                "task_count": 20,
                "canonical_drift_tasks": 10,
                "ordinary_ascii_tasks": 10,
                "active_visible_constraint_tasks": 0,
                "exposure_assignment_reads_only_pre_registered_visible_column_bytes": True,
                "provider_response_prediction_truth_score_or_outcome_used": False,
            },
        )

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with (
            mock.patch.object(
                target,
                "_history_freshness",
                return_value=copy.deepcopy(self.freshness),
            ),
            mock.patch.object(
                target,
                "_tests",
                return_value={
                    "expected": target.EXPECTED_TESTS,
                    "observed": target.EXPECTED_TESTS,
                    "passed": True,
                    "suites": [],
                },
            ),
            mock.patch.object(
                target.watcher_base,
                "_watcher_observation",
                return_value={
                    "replacement_process_count": 0,
                    "agent_signal_stop_restart_or_replacement_performed": False,
                },
            ),
        ):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["authorization"][
                "fresh_canonical_totality_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_resealed_freshness_overlap_gate_credit_or_authority_tamper_fails(self) -> None:
        with (
            mock.patch.object(
                target,
                "_history_freshness",
                return_value=copy.deepcopy(self.freshness),
            ),
            mock.patch.object(
                target,
                "_tests",
                return_value={
                    "expected": target.EXPECTED_TESTS,
                    "observed": target.EXPECTED_TESTS,
                    "passed": True,
                    "suites": [],
                },
            ),
            mock.patch.object(
                target.watcher_base,
                "_watcher_observation",
                return_value={
                    "replacement_process_count": 0,
                    "agent_signal_stop_restart_or_replacement_performed": False,
                },
            ),
        ):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("freshness", "overlap", "gate", "credit", "authority"):
            changed = copy.deepcopy(value)
            if kind == "freshness":
                changed["selection_freshness"][
                    "tree_exact_literal_match_line_count"
                ] = 1
            elif kind == "overlap":
                first = next(iter(changed["overlap"]["historical_population_overlaps"]))
                changed["overlap"]["historical_population_overlaps"][first][
                    "identity_overlap_count"
                ] = 1
            elif kind == "gate":
                changed["quality_gate"][
                    "minimum_arm_blind_paired_complete_tasks"
                ] = 1
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
