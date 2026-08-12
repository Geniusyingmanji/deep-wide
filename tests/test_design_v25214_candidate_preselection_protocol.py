from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25214_candidate_preselection_protocol as target  # noqa: E402


class V25214CandidatePreselectionProtocolDesignTests(unittest.TestCase):
    @staticmethod
    def _pool() -> dict[str, list[str]]:
        return {
            stratum: [f"candidate-{index}-{stratum}" for index in range(64)]
            for stratum in target.SAMPLING_STRATA
        }

    @staticmethod
    def _hashes() -> dict[str, str]:
        return {
            stratum: f"{index + 1:064x}"
            for index, stratum in enumerate(target.SAMPLING_STRATA)
        }

    def test_parent_selector_build_audit_is_exactly_bound(self) -> None:
        self.assertTrue(target._parent_barrier())

    def test_four_sampling_strata_are_distinct_from_four_epistemic_variables(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(len(value["sampling_strata"]), 4)
        self.assertEqual(len(value["epistemic_risk_variables"]), 4)
        self.assertTrue(
            set(value["sampling_strata"]).isdisjoint(
                value["epistemic_risk_variables"]
            )
        )
        self.assertTrue(
            value[
                "sampling_strata_are_not_epistemic_risk_estimates_or_benchmark_labels"
            ]
        )

    def test_deterministic_selection_is_order_invariant_and_exact_four_by_16(self) -> None:
        pool = self._pool()
        hashes = self._hashes()
        first = target.select_candidates(pool, snapshot_hashes=hashes)
        reversed_pool = {stratum: list(reversed(rows)) for stratum, rows in pool.items()}
        second = target.select_candidates(reversed_pool, snapshot_hashes=hashes)
        self.assertEqual(first, second)
        self.assertEqual(
            {stratum: len(rows) for stratum, rows in first.items()},
            {stratum: 16 for stratum in target.SAMPLING_STRATA},
        )

    def test_snapshot_hash_changes_rank_and_invalid_hash_fails_closed(self) -> None:
        identity = "candidate"
        first = target.deterministic_rank(
            target.SAMPLING_STRATA[0], identity, snapshot_sha256="1" * 64
        )
        second = target.deterministic_rank(
            target.SAMPLING_STRATA[0], identity, snapshot_sha256="2" * 64
        )
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            target.deterministic_rank(
                target.SAMPLING_STRATA[0], identity, snapshot_sha256="short"
            )

    def test_undersized_or_cross_stratum_collision_fails_closed(self) -> None:
        pool = self._pool()
        pool[target.SAMPLING_STRATA[0]].pop()
        with self.assertRaises(RuntimeError):
            target.select_candidates(pool, snapshot_hashes=self._hashes())
        pool = self._pool()
        pool[target.SAMPLING_STRATA[1]] = list(pool[target.SAMPLING_STRATA[0]])
        with self.assertRaises(RuntimeError):
            target.select_candidates(pool, snapshot_hashes=self._hashes())

    def test_design_authorizes_discovery_build_only(self) -> None:
        authorization = target.build_design(now=1)["authorization"]
        self.assertTrue(
            authorization["deterministic_candidate_discovery_implementation_build_only"]
        )
        self.assertFalse(authorization["public_index_snapshot_network_access"])
        self.assertFalse(authorization["real_identity_selection_or_population_freeze"])
        self.assertFalse(
            authorization["probe_runtime_integration_external_forward_or_activation"]
        )

    def test_resealed_stratum_risk_sampling_authority_or_credit_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in ("stratum", "risk", "sampling", "authority", "credit"):
            changed = copy.deepcopy(value)
            if kind == "stratum":
                changed["sampling_strata"][0] = "hidden_anchor_A"
            elif kind == "risk":
                changed["separation_contract"][
                    "A_M_Re_Yec_not_estimated_calibrated_routed_or_credited_by_this_gate"
                ] = False
            elif kind == "sampling":
                changed["sampling_contract"]["manual_reordering_replacement_or_selective_backfill"] = True
            elif kind == "authority":
                changed["authorization"]["public_index_snapshot_network_access"] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)


if __name__ == "__main__":
    unittest.main()
