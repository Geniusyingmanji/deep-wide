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

from scripts import audit_v24764_control_plane_build_readiness as target  # noqa: E402


class V24764ControlPlaneBuildReadinessTests(unittest.TestCase):
    def test_parent_manifest_ast_and_transport_contract_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.ast_findings(), ([], []))
        self.assertEqual(
            set(target._manifest()), {str(path) for path in target.SOURCES}
        )
        compatibility = target.compatibility_contract()
        self.assertTrue(compatibility["compatible"])
        self.assertEqual(compatibility["runtime_owned_task_union_wrapper_call_count"], 1)

    def test_work_order_is_exact_append_only_and_pristine(self) -> None:
        self.assertEqual(len(target.PLANNED_RUNTIME_SOURCES), 5)
        self.assertEqual(len(target.PLANNED_AUDIT_SOURCES), 4)
        self.assertEqual(len(target.PLANNED_RUNTIME_KEYS), 13)
        self.assertTrue(
            all(
                not (target.ROOT / path).exists()
                and not (target.ROOT / path).is_symlink()
                for path in (*target.PLANNED_SOURCES, *target.FUTURE_RESULTS)
            )
        )

    def test_direct_hard_wall_inner_prevents_double_union_and_title_backfill(self) -> None:
        value = target.compatibility_contract()
        self.assertEqual(value["planned_search_inner_class"], "HardTotalWallNativeSearchClient")
        self.assertEqual(value["task_union_wrapper_class"], "TaskUnionDiscoverySearchClient")
        self.assertFalse(value["double_task_union_wrapper_allowed"])
        self.assertEqual(value["thin_title_backfill_or_second_runtime_import_markers"], [])

    def test_resealed_launch_or_package_artifact_authority_tamper_fails(self) -> None:
        manifest = {"x": "a" * 64}
        compatibility = target.compatibility_contract()
        parent = target._read(target.PARENT)
        value = {
            "role": "v24764_control_plane_build_readiness",
            "parent_protocol_sha256": "b" * 64,
            "correction_sha256": "c" * 64,
            "dependency_manifest": manifest,
            "dependency_manifest_sha256": target.payload_sha256(manifest),
            "inherited_scientific_contract": {
                "runtime_sha256": target.payload_sha256(parent["runtime"]),
                "forward_health_gate_sha256": target.payload_sha256(
                    parent["forward_health_gate"]
                ),
                "mechanism_gate_sha256": target.payload_sha256(
                    parent["mechanism_gate_before_private_truth"]
                ),
                "quality_gate_sha256": target.payload_sha256(
                    parent["quality_gate_after_prediction_freeze"]
                ),
                "entropy_credit_scope_sha256": target.payload_sha256(
                    parent["entropy_credit_scope"]
                ),
                "task_runtime_input_keys": ["opaque_id", "question"],
                "task_count": 8,
                "science_contract_mutable_by_source_build": False,
            },
            "transport_compatibility": compatibility,
            "work_order": {
                "planned_runtime_sources": [str(path) for path in target.PLANNED_RUNTIME_SOURCES],
                "planned_audit_and_test_sources": [str(path) for path in target.PLANNED_AUDIT_SOURCES],
                "required_runtime_contracts": list(target.PLANNED_RUNTIME_KEYS),
                "planned_sources_pristine": True,
                "future_result_and_output_surfaces_pristine": True,
                "append_only_implementation": True,
                "private_population_or_truth_not_in_forward_manifest": True,
                "source_build_may_open_private_population": False,
                "package_audit_may_open_private_population": False,
            },
            "tests": {
                "passed": True,
                "observed": 49,
                "expected": 49,
                "suites": [
                    {
                        "path": str(path),
                        "expected": expected,
                        "observed": expected,
                        "return_code": 0,
                        "output_sha256": "d" * 64,
                        "passed": True,
                    }
                    for path, expected in target.TEST_SUITES
                ],
                "network_model_search_fetch_benchmark_or_evaluator_called": False,
            },
            "label_blind_audit": {
                "privileged_accesses": [],
                "evaluator_or_gold_imports": [],
                "passed": True,
            },
            "runtime_state": {
                "protected_watchers": [],
                "shared_api_lease_inactive": True,
                "v24765_runner_active": False,
            },
            "git": {"repository_clean": True, "head_equals_target_main": True},
            "source_policy": {
                "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "private_population_truth_provenance_or_quality_opened_or_hashed": False,
                "credential_read_hashed_persisted_or_emitted": False,
                "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
            },
            "findings": [],
            "audit_valid": True,
            "authorization": {
                "v24765_control_plane_source_implementation_and_local_tests": True,
                "v24766_package_audit_source_implementation": True,
                "source_commit_and_push": True,
                "package_audit_artifact_generation": False,
                "preactivation_audit": False,
                "activation": False,
                "execution_start": False,
                "external_launch": False,
                "private_truth_or_quality_surface_open": False,
                "paired_dev64": False,
                "exact220": False,
                "entropy_or_credit_experiment": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(
                target,
                "sha256",
                side_effect=lambda path: "b" * 64
                if path == target.ROOT / target.PARENT
                else "c" * 64,
            ),
            patch.object(target, "_manifest", return_value=manifest),
            patch.object(target, "_watchers", return_value=[]),
        ):
            self.assertEqual(target.validate_audit(value), value)
            for field in ("external_launch", "package_audit_artifact_generation"):
                altered = copy.deepcopy(value)
                altered["authorization"][field] = True
                altered.pop("audit_payload_sha256")
                altered["audit_payload_sha256"] = target.payload_sha256(altered)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(altered)

    def test_expected_suite_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count in target.TEST_SUITES), 49)
        self.assertEqual(target.EXPECTED_TESTS, 49)


if __name__ == "__main__":
    unittest.main()
