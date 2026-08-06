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

from scripts import audit_v24755_generic_structured_adapter_build as target  # noqa: E402


class V24755GenericStructuredAdapterBuildAuditTests(unittest.TestCase):
    def test_real_parent_manifest_ast_and_zero_effect_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.ast_findings(), ([], []))
        self.assertEqual(set(target._manifest()), {str(path) for path in target.SOURCES})
        self.assertEqual(
            target._zero_effect_probe(),
            {
                "candidate_identity_on_empty_pages": True,
                "ordinary_record_count": 0,
                "changed_cell_count": 0,
                "additional_model_requests": 0,
                "additional_logical_queries": 0,
                "additional_search_batches": 0,
                "additional_provider_search_calls": 0,
                "additional_fetch_calls": 0,
                "positive_entropy_or_task_credit_assigned": False,
            },
        )

    def test_resealed_launch_authority_tamper_fails(self) -> None:
        manifest = {"x": "a" * 64}
        value = {
            "role": "v24755_generic_structured_adapter_build_audit",
            "parent_reachability_audit_sha256": "b" * 64,
            "dependency_manifest": manifest,
            "dependency_manifest_sha256": target.payload_sha256(manifest),
            "tests": {"passed": True, "observed": 23, "expected": 23},
            "label_blind_audit": {
                "privileged_accesses": [],
                "external_capability_imports": [],
                "passed": True,
            },
            "zero_effect_probe": target._zero_effect_probe(),
            "runtime_state": {
                "protected_watchers": [],
                "shared_api_lease_inactive": True,
                "runner_active": False,
            },
            "git": {"repository_clean": True, "head_equals_target_main": True},
            "source_policy": {
                "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
                "credential_read_hashed_persisted_or_emitted": False,
                "runtime_input_is_baseline_and_already_fetched_pages_only": True,
            },
            "findings": [],
            "audit_valid": True,
            "authorization": {
                "fresh_external_population_and_protocol_design": True,
                "external_launch": False,
                "paired_dev64_protocol_or_launch": False,
                "evaluator": False,
                "exact220": False,
                "entropy_or_credit_experiment": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        with (
            patch.object(target, "sha256", return_value="b" * 64),
            patch.object(target, "_manifest", return_value=manifest),
            patch.object(target, "_watchers", return_value=[]),
        ):
            target.validate_audit(value)
            altered = copy.deepcopy(value)
            altered["authorization"]["external_launch"] = True
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_audit(altered)


if __name__ == "__main__":
    unittest.main()
