from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24729_dual_namespace_population_capacity_repair as target  # noqa: E402


class V24729CapacityRepairTests(unittest.TestCase):
    def test_repair_changes_only_cap_roles_and_append_only_parent(self) -> None:
        private_ror = {
            "role": "v24727_ror_evaluator_only_population",
            "private_payload_sha256": "x",
        }
        private_wb = {
            "role": "v24727_worldbank_evaluator_only_population",
            "selection_rule": "old",
            "private_payload_sha256": "x",
        }
        public = {
            "role": "v24727_dual_namespace_population_design",
            "parents": {},
            "clusters": {
                "ror": {"private_population_file_sha256": "x"},
                "worldbank": {
                    "selected_country_count": 48,
                    "task_count": 12,
                    "selected_region_max": 10,
                    "private_population_file_sha256": "x",
                },
            },
            "source_policy": {"forbidden": False},
        }
        with patch.object(target, "sha256", return_value="a" * 64):
            ror, wb, repaired = target.repair_artifacts(
                private_ror, private_wb, public
            )
        self.assertEqual(ror["role"], "v24729_ror_evaluator_only_population")
        self.assertEqual(wb["role"], "v24729_worldbank_evaluator_only_population")
        self.assertEqual(repaired["capacity_repair"]["minimum_feasible_region_cap"], 10)
        self.assertTrue(repaired["capacity_repair"]["only_region_cap_changed"])
        self.assertFalse(repaired["authorization"]["forward_launch"])

    def test_resealed_launch_or_cap_tamper_fails_closed(self) -> None:
        with patch.object(target, "sha256", return_value="a" * 64):
            value = {
                "role": "v24729_dual_namespace_population_design",
                "parents": {"v24728_capacity_diagnosis_sha256": "a" * 64},
                "capacity_repair": {
                    "predecessor_v24727_output_surfaces_pristine": True,
                    "failed_region_cap": 9,
                    "failed_cap_capacity": 46,
                    "minimum_feasible_region_cap": 10,
                    "minimum_feasible_cap_capacity": 51,
                    "indicator_rank_exclusion_or_grouping_rule_changed": False,
                    "only_region_cap_changed": True,
                },
                "clusters": {
                    "worldbank": {
                        "region_cap": 10,
                        "selected_country_count": 48,
                        "task_count": 12,
                        "selected_region_max": 10,
                        "selection_rule": "complete_two_fresh_indicator_values_prior_external_iso3_exclusion_v24727_sha256_rank_region_cap10_round_robin_groups4",
                    }
                },
                "source_policy": {"forbidden": False},
                "authorization": {
                    "dual_namespace_reachability_protocol_design": True,
                    "population_publication_only": True,
                    "forward_launch": False,
                    "evaluator": False,
                    "benchmark_dev64_or_exact220": False,
                    "entropy_or_credit_claim": False,
                    "leaderboard_or_sota": False,
                },
            }
            value["design_payload_sha256"] = target.payload_sha256(value)
            target.validate_public(value)
            for field, replacement in (("forward_launch", True), ("benchmark_dev64_or_exact220", True)):
                tampered = copy.deepcopy(value)
                tampered["authorization"][field] = replacement
                tampered.pop("design_payload_sha256")
                tampered["design_payload_sha256"] = target.payload_sha256(tampered)
                with self.assertRaises(RuntimeError):
                    target.validate_public(tampered)

    def test_parent_authorizes_population_only(self) -> None:
        self.assertEqual(target.REPAIRED_REGION_CAP, 10)
        self.assertNotEqual(target.OUTPUT, target.base.OUTPUT)
        self.assertNotEqual(target.PRIVATE_ROR, target.base.PRIVATE_ROR)
        self.assertNotEqual(target.PRIVATE_WB, target.base.PRIVATE_WB)


if __name__ == "__main__":
    unittest.main()
