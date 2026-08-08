from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24841_four_run_structure_closure as target  # noqa: E402


class V24841FourRunStructureClosureDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build(now=1)

    def test_four_exact220_denominators_and_parent_chains(self) -> None:
        self.assertTrue(self.value["checks"]["all_four_parent_chains_valid"])
        self.assertTrue(
            self.value["checks"]["all_four_metric_and_task_denominators_exact220"]
        )
        self.assertTrue(all(row["n"] == 220 for row in self.value["aggregates"].values()))

    def test_v24840_point_gain_is_not_statistically_resolved(self) -> None:
        pair = self.value["paired_to_v24840"]["v24837_to_v24840"]
        low, high = pair["composite_task_cluster_bootstrap"][
            "percentile_95_interval"
        ]
        self.assertLessEqual(low, 0)
        self.assertGreaterEqual(high, 0)
        self.assertFalse(
            self.value["conclusions"][
                "v24840_vs_v24837_composite_ci_excludes_zero"
            ]
        )

    def test_synthetic_orphan_table_header_defect_is_reproduced(self) -> None:
        witness = self.value["synthetic_structure_witness"]
        self.assertTrue(witness["target_tail_row_retained"])
        self.assertFalse(witness["table_header_retained"])
        self.assertTrue(witness["orphan_target_row_without_table_header"])

    def test_no_historical_score_routes_future_forward(self) -> None:
        self.assertFalse(
            self.value["boundary"][
                "historical_metric_transition_or_stratum_authorized_as_future_runtime_input"
            ]
        )
        self.assertFalse(
            self.value["conclusions"][
                "historical_score_or_transition_may_route_future_forward"
            ]
        )

    def test_authorization_is_build_only(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["table_header_closure_projector_build"])
        self.assertFalse(authorization["external_launch"])
        self.assertFalse(authorization["public_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator"])
        self.assertFalse(authorization["leaderboard_or_sota"])


if __name__ == "__main__":
    unittest.main()
