from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.dispose_v24202_webswarm_baseline_only import (
    ROOT,
    build_disposition,
    publish_new,
)


class DisposeV24202WebSwarmBaselineOnlyTests(unittest.TestCase):
    def test_disposition_is_baseline_only_and_nonexecuting(self) -> None:
        value = build_disposition(ROOT, created_at_unix=1)
        disposition = value["disposition"]
        self.assertEqual(
            disposition["decision"], "baseline_only_not_mainline_component"
        )
        self.assertFalse(disposition["v24202_eligible_for_v24200_component_set"])
        self.assertFalse(
            disposition["v24202_eligible_for_integrated_candidate_package"]
        )
        self.assertTrue(
            disposition["future_arm_must_derive_from_selected_baseline_bytes"]
        )
        self.assertTrue(disposition["future_reportable_score_requires_fresh_exact220"])
        self.assertTrue(
            disposition[
                "future_same_model_search_backend_user_prompt_output_contract_budget_and_attempts_required"
            ]
        )
        self.assertTrue(
            disposition["future_method_specific_system_instructions_frozen_and_disclosed"]
        )
        self.assertTrue(disposition["future_all_system_instruction_input_tokens_counted"])
        self.assertFalse(value["authorization"]["candidate_build_materialization_or_package_gate"])
        self.assertFalse(
            value["authorization"]["benchmark_forward_dev64_full220_or_evaluator_launch"]
        )

    def test_unimplemented_features_are_explicit(self) -> None:
        value = build_disposition(ROOT, created_at_unix=1)
        missing = set(value["implementation_boundary"]["not_available"])
        self.assertIn("production_runtime_integration", missing)
        self.assertIn("sibling_trajectory_experience_reuse", missing)
        self.assertIn("no_web_probing_ablation", missing)
        self.assertIn("quality_cost_or_benchmark_effect", missing)
        self.assertTrue(
            value["implementation_boundary"][
                "unimplemented_features_must_not_be_reported_as_ablations"
            ]
        )

    def test_parent_drift_fails_closed(self) -> None:
        with mock.patch(
            "scripts.dispose_v24202_webswarm_baseline_only.V24202_AUDIT_SHA256",
            "0" * 64,
        ), self.assertRaisesRegex(RuntimeError, "drifted"):
            build_disposition(ROOT, created_at_unix=1)

    def test_publish_rejects_noncanonical_output(self) -> None:
        value = build_disposition(ROOT, created_at_unix=1)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", value)


if __name__ == "__main__":
    unittest.main()
