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

from scripts import audit_v25414_fresh_paired_rfc_route_population as target  # noqa: E402


class V25414FreshPairedRfcRoutePopulationAuditTests(unittest.TestCase):
    def test_fixed_parent_and_aggregate_history_scan_are_zero(self) -> None:
        self.assertEqual(
            target._git(
                "rev-parse", target.population.FRESHNESS_PARENT_COMMIT
            ).stdout.strip(),
            target.population.FRESHNESS_PARENT_COMMIT,
        )
        self.assertEqual(target._aggregate_history_scan(), (0, 0))

    def test_audit_binds_first_candidate_and_fixed_vectors(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(value["selected_first_zero_collision_interval"], "RFC 9320-9399")
        self.assertEqual(value["pair_count"], 20)
        self.assertEqual(value["task_count"], 40)
        self.assertEqual(value["identity_count"], 80)
        self.assertEqual(
            value["identity_vector_sha256"],
            target.population.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            value["pair_vector_sha256"],
            target.population.EXPECTED_PAIR_VECTOR_SHA256,
        )
        self.assertEqual(
            value["task_vector_sha256"],
            target.population.EXPECTED_TASK_VECTOR_SHA256,
        )

    def test_audit_is_fail_closed_on_collision_or_vector_tamper(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("tree", "history", "vector", "selection"):
            changed = copy.deepcopy(value)
            if kind == "tree":
                changed["canonical_identity_and_slug_tree_match_count"] = 1
            elif kind == "history":
                changed[
                    "canonical_identity_and_slug_history_introduction_count"
                ] = 1
            elif kind == "vector":
                changed["pair_vector_sha256"] = "a" * 64
            else:
                changed["selected_first_zero_collision_interval"] = "RFC 9240-9319"
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.population.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_no_external_effect_or_launch_authority(self) -> None:
        with mock.patch.object(
            target, "_aggregate_history_scan", return_value=(0, 0)
        ):
            value = target.build_audit(now=1)
        self.assertFalse(value["candidate_page_endpoint_model_evaluator_or_quality_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_benchmark_or_api_called"])
        self.assertFalse(value["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(
            value["authorization"][
                "network_model_search_fetch_external_forward_or_evaluator"
            ]
        )
        self.assertFalse(
            value["authorization"][
                "deepwidebench_forward_evaluator_leaderboard_or_sota"
            ]
        )


if __name__ == "__main__":
    unittest.main()
