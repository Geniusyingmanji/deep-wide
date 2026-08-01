from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24230_mica_credit_baseline import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24230MicaCreditBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_equations_variable_horizon_cost_and_limits(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "paper_immediate_idr_equation_replayed",
            "discounted_monte_carlo_return_equation_replayed",
            "same_prompt_same_turn_population_normalization_replayed",
            "same_prompt_all_valid_turn_population_normalization_replayed",
            "convex_mixed_advantage_replayed",
            "variable_horizon_eligible_trajectory_normalization_replayed",
            "state_and_potential_continuity_replayed",
            "dense_feedback_cost_aggregation_replayed",
            "nested_privileged_runtime_metadata_rejected",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "dense_feedback_semantic_correctness_independently_verified",
            "potential_is_causal_state_value",
            "same_state_causal_identification",
            "independent_outer_target_used",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_static_audit_rejects_expansive_capabilities_and_privilege(
        self,
    ) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "import pathlib\ndef x(): return pathlib.Path('x').read_text()\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return getattr(v, 'secret')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_is_sealed_label_blind_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["baseline_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_mica_baseline_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_guard_has_no_v24230_import(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertEqual(guard["file_count"], 5)
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )

    def test_control_sources_have_no_credentials_or_concrete_opaque_ids(self) -> None:
        scan = self.value["control_source_forbidden_literal_scan"]
        self.assertEqual(scan["file_count"], 4)
        self.assertEqual(scan["hit_count"], 0)
        self.assertFalse(scan["credential_or_concrete_opaque_id_literal_present"])

    def test_scientific_scope_discloses_noncausal_and_unproven_boundaries(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "mica_v3_immediate_idr_return_and_mixed_advantage_implemented",
            "gamma_domain_zero_excluded_and_one_included",
            "alpha_and_beta_convex_boundary_included",
            "population_not_sample_standard_deviation_implemented",
            "variable_horizon_eligible_turn_sets_implemented",
            "dense_feedback_calls_and_tokens_recorded",
            "dense_feedback_limited_to_training_or_calibration_scope",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "dense_feedback_semantic_correctness_proven",
            "potential_is_causal_state_value",
            "same_state_causal_identification",
            "independent_outer_target_used",
            "real_rollouts_or_dense_judgments_observed",
            "gate2b_evaluated",
            "training_effect_observed",
            "benchmark_quality_or_cost_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_create_exclusive_no_follow_and_fsyncs_file_and_parent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24230_mica_credit_baseline.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24230_mica_credit_baseline.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24230_mica_credit_baseline.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24230_mica_credit_baseline.os.fsync",
                    wraps=os.fsync,
                ) as fsync_mock,
            ):
                publish_new(target, self.value)
                self.assertGreaterEqual(fsync_mock.call_count, 2)
                first_flags = open_mock.call_args_list[0].args[1]
                self.assertTrue(first_flags & os.O_EXCL)
                self.assertTrue(first_flags & os.O_NOFOLLOW)
                with self.assertRaises(FileExistsError):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
