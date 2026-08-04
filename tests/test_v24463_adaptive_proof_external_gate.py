from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24463_adaptive_proof_external_gate as target  # noqa: E402


class V24463AdaptiveProofExternalGateTests(unittest.TestCase):
    def test_population_is_exact_and_canonically_disjoint(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target.QUESTIONS), 16)
        self.assertEqual(len(target._prior_questions()), 252)
        self.assertEqual(
            [set(target.neutral_task(i)) for i in range(1, 17)],
            [{"opaque_id", "question"}] * 16,
        )

    def test_protocol_is_design_only_and_persists_no_task_content(self) -> None:
        with (
            patch.object(target, "_manifest", return_value={"a": "b"}),
            patch.object(target, "_build_parent"),
            patch.object(target, "validate_protocol", side_effect=lambda _root, value: value),
            patch.object(target, "_future", return_value=True),
        ):
            value = target.build_protocol(now=0)
        encoded = json.dumps(value, ensure_ascii=False)
        for ordinal in range(1, target.SELECTED + 1):
            task = target.neutral_task(ordinal)
            self.assertNotIn(task["opaque_id"], encoded)
            self.assertNotIn(task["question"], encoded)
        self.assertTrue(
            value["authorization"]["one_fresh_adaptive_proof_external_probe_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["benchmark_launch"])

    def test_mechanism_contract_freezes_adaptive_proof_and_zero_replay(self) -> None:
        value = target._mechanism_contract()
        self.assertEqual(value["maximum_additional_fetches"], 3)
        self.assertEqual(value["total_fetch_cap"], 13)
        self.assertEqual(value["additional_model_requests"], 0)
        self.assertEqual(value["additional_provider_search_calls"], 0)
        self.assertTrue(value["projection_consumes_only_validated_capability"])
        self.assertFalse(value["parent_recursive_historical_replay"])
        self.assertFalse(value["public_projection_contains_lead_page_or_hash"])

    def test_public_result_rejects_content_and_replay_tamper(self) -> None:
        mechanism = {
            "selected": 16,
            "exact_ordinal_vector": True,
            "passed_tasks": 16,
            "failed_tasks": 0,
            "all_threshold_partitions_exact": True,
            "all_effects_conserved": True,
            "all_single_validation_attested": True,
            "all_projections_consumed_validated_capabilities": True,
            "total_adaptive_safe_change_count": 1,
            "total_adaptive_additional_fetch_calls": 16,
            "total_adaptive_final_decision_credit_total_nats": 1.0,
        }
        observation = {
            "selected": 16,
            "exact_ordinal_vector": True,
            "success_tasks": 16,
            "failure_tasks": 0,
            "fully_observed_effect_tasks": 16,
            "slot_timeouts_lower_bound": 0,
            "provider_deadline_failures_lower_bound": 0,
            "hosted_search_deadline_failures_lower_bound": 0,
            "hard_fetch_deadline_failures_lower_bound": 0,
            "fetch_helper_failures_lower_bound": 0,
            "unobserved_effect_tasks": 0,
        }
        timing = {
            "selected": 16,
            "exact_ordinal_vector": True,
            "parent_success_tasks": 16,
            "certificate_validation_invocations": 16,
            "adaptive_projection_invocations": 16,
            "capability_observation_tasks": 16,
            "capability_adaptive_projection_tasks": 16,
            "failure_lower_bound_observation_tasks": 0,
            "recursive_historical_semantic_replay_tasks": 0,
            "parent_certificate_validation_wall_p95_seconds": 0.02,
        }
        value = {
            "artifact_version": 1,
            "role": "v24463_adaptive_proof_external_result",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 0,
            "selected": 16,
            "executor_count": 8,
            "model_slot_cap": 2,
            "batch_wall_seconds": 100.0,
            "mechanism_aggregate": mechanism,
            "observation_aggregate": observation,
            "stage_timing_aggregate": timing,
            "mechanism_failure_as_zero_rows": 0,
            "mechanism_passed": True,
            "reliability_passed": True,
            "parent_validation_passed": True,
            "latency_passed": True,
            "diagnostic_complete": True,
            "passed": True,
            "temporary_execution_directory_remaining": False,
            "private_task_or_web_content_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "provenance": {name: "a" * 64 for name in (
                "protocol_sha256",
                "preactivation_audit_sha256",
                "activation_sha256",
                "execution_start_sha256",
                "surface_manifest_sha256",
            )},
        }
        value["result_payload_sha256"] = payload_sha256(value)
        with (
            patch.object(target, "validate_mechanism_aggregate"),
            patch.object(target, "validate_observation_aggregate"),
            patch.object(target, "validate_stage_timing_aggregate"),
        ):
            target.validate_public_result(value)
            for field in ("recursive_replay", "private_content"):
                altered = copy.deepcopy(value)
                if field == "recursive_replay":
                    altered["stage_timing_aggregate"][
                        "recursive_historical_semantic_replay_tasks"
                    ] = 1
                else:
                    altered["private_task_or_web_content_persisted"] = True
                altered.pop("result_payload_sha256")
                altered["result_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(RuntimeError):
                    target.validate_public_result(altered)

    def test_runtime_source_is_label_blind(self) -> None:
        accesses, imports = target.build_audit.base._ast_findings(
            Path(target.RUNNER_MARKER)
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
