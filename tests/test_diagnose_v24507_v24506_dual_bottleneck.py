from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24507_v24506_dual_bottleneck as target  # noqa: E402


PROFILE = {
    "synthetic_execution_count": 1,
    "high_level_validator_calls": {"v24457": 107, "v24490": 11, "v24496": 5},
    "low_level_validation_memo_calls": 1687,
    "low_level_validation_memo_misses": 8,
    "low_level_validation_memo_hits": 1679,
    "low_level_validation_memo_mismatches": 0,
    "synthetic_wall_seconds": 1.0,
    "synthetic_clients_only": True,
    "task_question_identifier_query_url_page_prediction_or_value_emitted": False,
    "network_model_search_fetch_process_or_evaluator_called": False,
}


class V24507V24506DualBottleneckDiagnosisTests(unittest.TestCase):
    def test_public_closed_parent_builds_dual_diagnosis(self) -> None:
        with patch.object(target, "_profile_synthetic", return_value=PROFILE):
            value = target.build_report(now=0)
        self.assertTrue(
            value["diagnosis"][
                "post_effect_local_validation_amplification_observed"
            ]
        )
        self.assertTrue(
            value["diagnosis"]["target_plan_coverage_dead_zone_observed"]
        )
        self.assertFalse(
            value["diagnosis"]["record_bound_projector_externally_exercised"]
        )
        self.assertFalse(value["authorization"]["same_population_rerun"])
        target.validate_report(value)

    def test_profile_and_public_evidence_tamper_fail_closed(self) -> None:
        with patch.object(target, "_profile_synthetic", return_value=PROFILE):
            value = target.build_report(now=0)
        for path, replacement in (
            (("synthetic_profile", "low_level_validation_memo_misses"), 7),
            (("public_result_evidence", "worker_hard_timeout_tasks"), 0),
            (("diagnosis", "target_plan_coverage_dead_zone_observed"), False),
            (("authorization", "same_population_rerun"), True),
        ):
            changed = copy.deepcopy(value)
            changed[path[0]][path[1]] = replacement
            changed.pop("diagnosis_payload_sha256")
            from deepwide_agent.v24320_forward_contract import payload_sha256

            changed["diagnosis_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(ValueError):
                target.validate_report(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/diagnose_v24507_v24506_dual_bottleneck.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
