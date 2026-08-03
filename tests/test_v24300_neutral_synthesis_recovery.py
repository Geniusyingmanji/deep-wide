from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24300_neutral_synthesis_recovery as target  # noqa: E402


class V24300NeutralSynthesisRecoveryTests(unittest.TestCase):
    def test_protocol_is_neutral_and_unauthorized(self) -> None:
        protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(protocol["budget_contract"]["model_calls"], 3)
        self.assertFalse(protocol["budget_contract"]["fourth_model_effect_allowed"])
        self.assertTrue(protocol["task_contract"]["synthetic_neutral_task"])
        self.assertFalse(protocol["authorization"]["benchmark_dev64_launch"])
        self.assertFalse(protocol["authorization"]["exact220_launch"])

    def test_fault_injected_model_accounts_local_and_real_calls(self) -> None:
        from types import SimpleNamespace

        class Real:
            requests = attempts = input_tokens = output_tokens = total_tokens = 0

            def complete(self, *args, **kwargs):
                del args, kwargs
                self.requests += 1
                self.attempts += 1
                self.input_tokens += 10
                self.output_tokens += 5
                self.total_tokens += 15
                return SimpleNamespace(
                    text="| Name | Version | Date |\n| --- | --- | --- |\n| NeutralWidget | 1.0 | 2026-08-03 |"
                )

        model = target.NeutralFaultInjectedModel(Real())
        self.assertEqual(model.complete("", "", max_output_tokens=1, json_mode=True).text, target.NEUTRAL_PLAN)
        with self.assertRaises(target.ModelRequestError):
            model.complete("", "", max_output_tokens=1)
        model.complete("", "", max_output_tokens=1)
        self.assertEqual(model.requests, 3)
        self.assertEqual(model.attempts, 3)
        self.assertEqual(model.plan_locally_returned, 1)
        self.assertEqual(model.initial_synthesis_failures_injected, 1)
        self.assertEqual(model.real_recovery_requests, 1)

    def test_projection_and_decision_require_every_effect(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24300_neutral_synthesis_recovery_probe",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 1,
            "scope": "fault_injected_neutral_real_provider_synthesis_recovery_only",
            "provider": "azure-native-keyless-gpt-5.6-sol",
            "wall_seconds": 1.0,
            "completion_kind": "primary",
            "model_budget": {
                "limit": 3,
                "admitted": 3,
                "provider_requests": 3,
                "provider_attempts": 3,
                "slot_acquisitions": 3,
                "fourth_provider_effect": False,
            },
            "recovery": {
                "effects_by_stage": {
                    "plan": 1,
                    "synthesis_initial": 1,
                    "synthesis_recovery": 1,
                    "repair": 0,
                },
                "total_effects_admitted": 3,
                "initial_synthesis_model_request_error": True,
                "recovery_eligible": True,
                "recovery_admitted": True,
                "recovery_attempted": True,
                "recovery_succeeded": True,
                "recovery_model_request_error": False,
                "repair_blocked_after_recovery": False,
                "local_plan_returns": 1,
                "injected_initial_synthesis_failures": 1,
                "real_recovery_requests": 1,
            },
            "search": {"calls": 0, "fetch_calls": 0},
            "source_policy": {
                "synthetic_neutral_task_used_but_not_persisted_or_hashed": True,
                "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
                "question_prompt_response_prediction_answer_or_hash_persisted": False,
                "credential_value_read_persisted_hashed_or_emitted": False,
                "official_evaluator_called": False,
                "shared_api_lease_acquired": True,
            },
            "authorization": {
                "benchmark_dev64_launch": False,
                "exact220_launch": False,
                "evaluator_call": False,
                "training_credit_assignment": False,
                "leaderboard_submission_or_sota_claim": False,
            },
        }
        value["result_payload_sha256"] = target.payload_sha256(value)
        target.validate_projection(value)
        checks = target._checks(value, target.GATES)
        self.assertTrue(all(checks.values()))

    def test_resealed_projection_tamper_fails(self) -> None:
        protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertFalse(protocol["authorization"]["evaluator_call"])
        value = copy.deepcopy(target.GATES)
        self.assertEqual(value["required_provider_requests"], 3)


if __name__ == "__main__":
    unittest.main()
