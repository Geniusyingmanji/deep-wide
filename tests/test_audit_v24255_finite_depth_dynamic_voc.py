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

from scripts.audit_v24255_finite_depth_dynamic_voc import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24255FiniteDepthDynamicVocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_three_policies_option_value_and_abstention(
        self,
    ) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "pure_information_gain_policy_replayed",
            "myopic_terminal_loss_voc_policy_replayed",
            "finite_depth_bellman_voc_policy_replayed",
            "high_ig_low_terminal_value_counterexample_replayed",
            "low_ig_high_terminal_value_counterexample_replayed",
            "myopic_zero_dynamic_positive_bridge_replayed",
            "descendant_option_value_replayed",
            "depth_one_equals_myopic_replayed",
            "hard_budget_and_stop_action_replayed",
            "missing_calibration_abstention_replayed",
            "nested_privileged_runtime_metadata_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(
            replay[
                "synthetic_benchmark_rows_or_real_evaluator_payload_read"
            ]
        )

    def test_static_audit_rejects_capabilities_and_privileged_reads(
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
                with self.assertRaisesRegex(
                    RuntimeError, "capability boundary"
                ):
                    audit_python_source(source)

    def test_receipt_is_sealed_label_blind_build_only_and_authorizes_nothing(
        self,
    ) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["build_only_dynamic_voc_kernel_available"]
        )
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["real_transition_model_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_guard_has_no_v24255_import(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_forward_entrypoints"]
        )
        self.assertEqual(guard["file_count"], 7)
        self.assertTrue(
            all(
                count == 0
                for count in guard["module_name_hit_count_by_file"].values()
            )
        )

    def test_control_sources_have_no_credentials_or_concrete_opaque_ids(
        self,
    ) -> None:
        scan = self.value["control_source_forbidden_literal_scan"]
        self.assertEqual(scan["file_count"], 4)
        self.assertEqual(scan["hit_count"], 0)
        self.assertFalse(
            scan["credential_or_concrete_opaque_id_literal_present"]
        )

    def test_scientific_scope_discloses_implemented_and_unproven_boundaries(
        self,
    ) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "same_action_graph_pure_ig_myopic_and_dynamic_voc_implemented",
            "finite_depth_bellman_recursion_implemented",
            "descendant_option_value_explicit",
            "heterogeneous_cost_and_hard_budget_implemented",
            "deterministic_value_per_cost_tie_break_implemented",
            "explicit_stop_and_missing_calibration_abstain_implemented",
            "cycle_unreachable_probability_and_budget_fail_closed",
            "terminal_loss_not_entropy_is_dynamic_utility",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "real_four_layer_loss_calibration_semantics_proven",
            "real_transition_probabilities_fitted_or_calibrated",
            "real_action_graph_or_rollout_observed",
            "runtime_integration_available",
            "gate2a_or_gate3a_evaluated",
            "benchmark_quality_or_cost_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_create_exclusive_no_follow_and_fsyncs_file_and_parent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24255_finite_depth_dynamic_voc.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24255_finite_depth_dynamic_voc.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24255_finite_depth_dynamic_voc.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24255_finite_depth_dynamic_voc.os.fsync",
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
