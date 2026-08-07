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

from scripts import audit_v24757_zero_effect_integration_build as target  # noqa: E402


class V24757ZeroEffectIntegrationBuildAuditTests(unittest.TestCase):
    def test_real_parent_manifest_and_ast_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.ast_findings(), ([], []))
        self.assertEqual(set(target._manifest()), {str(path) for path in target.SOURCES})

    def test_resealed_exact220_authority_tamper_fails(self) -> None:
        manifest = {"x": "a" * 64}
        value = {
            "role": "v24757_zero_effect_integration_build_audit",
            "parent_adapter_build_audit_sha256": "b" * 64,
            "dependency_manifest": manifest,
            "dependency_manifest_sha256": target.payload_sha256(manifest),
            "tests": {"passed": True, "observed": 29, "expected": 29},
            "label_blind_audit": {
                "privileged_accesses": [],
                "evaluator_imports": [],
                "passed": True,
            },
            "integration_contract": {
                "runtime_input_keys": ["opaque_id", "question"],
                "baseline_precedes_adapter": True,
                "adapter_pages_content_multiset_subset_of_synthesis_evidence": True,
                "redirect_resolved_final_url_required": True,
                "unfetched_snippet_or_search_narrative_replayed": False,
                "adapter_model_query_search_fetch_or_token_delta": 0,
                "ordinary_records_require_two_registrably_independent_sources": True,
                "nonunknown_cells_mutable": False,
                "entropy_or_prediction_change_positive_credit": False,
            },
            "runtime_state": {
                "protected_watchers": [],
                "shared_api_lease_inactive": True,
                "runner_active": False,
            },
            "git": {"repository_clean": True, "head_equals_target_main": True},
            "source_policy": {
                "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "network_model_search_fetch_benchmark_forward_or_evaluator_called_by_audit": False,
                "credential_read_hashed_persisted_or_emitted": False,
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
            altered["authorization"]["exact220"] = True
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_audit(altered)


if __name__ == "__main__":
    unittest.main()
