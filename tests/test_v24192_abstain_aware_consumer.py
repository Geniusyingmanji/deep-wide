from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24192_abstain_aware_gate2a import (
    CONTROL_FILES,
    ROOT,
    build_protocol,
)
from scripts.watch_v24192_abstain_aware_gate2a import run_once


class V24192AbstainAwareConsumerTests(unittest.TestCase):
    def test_protocol_freezes_exact_abstain_aware_contract(self) -> None:
        value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        self.assertEqual(
            value["protocol_id"],
            "v24192_abstain_aware_true_continuation_gate2a_consumer_v1",
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        contract = value["abstain_aware_contract"]
        self.assertEqual(contract["decisions"], ["action", "stop", "abstain"])
        self.assertTrue(contract["missing_signal_checkpoints_retained_in_primary_estimand"])
        self.assertTrue(contract["availability_matched_random_and_oracle_baselines"])
        self.assertTrue(
            contract["both_shared_cluster_bootstrap_minimum_lowers_strictly_positive"]
        )
        self.assertTrue(contract["parent_v24191_result_diagnostic_only_without_v24192"])
        self.assertFalse(value["authorization"]["training_credit"])
        self.assertFalse(value["authorization"]["full220_controller_launch"])

    def test_live_import_graph_is_canonical(self) -> None:
        code = (
            "import json,sys;"
            f"sys.path.insert(0,{str(ROOT)!r});"
            f"sys.path.insert(0,{str(ROOT / 'src')!r});"
            "from scripts.watch_v24192_abstain_aware_gate2a "
            "import assert_canonical_module_identity;"
            "print(json.dumps(assert_canonical_module_identity(),sort_keys=True))"
        )
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        environment["PYTHONSAFEPATH"] = "1"
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-c", code],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        identity = json.loads(completed.stdout)
        self.assertFalse(identity["forbidden_src_deepwide_agent_loaded"])
        self.assertEqual(
            identity["abstain_aware_evaluator_module"],
            "deepwide_agent.v24192_abstain_aware_gate2a",
        )

    @staticmethod
    def _parent(root: Path, *, terminal: bool = False, evaluated: bool = False) -> None:
        (root / "outputs").mkdir()
        parent = {
            "role": "v24191_policy_value_gate2a_consumer_state",
            "status": (
                "policy_value_gate2a_pass"
                if terminal and evaluated
                else "waiting_for_v24190_tie_aware_gate2a_terminal"
            ),
            "parent_status": "waiting_for_true_continuation_audit_terminal",
            "parent_source_status": "waiting_for_p12_trial2_exact220_release",
            "parent_source_truth_fields_all_false": True,
            "parent_terminal": False,
            "parent_tie_aware_gate2a_evaluated": False,
            "terminal": terminal,
            "activation_ready": True,
            "manifest_model_prediction_or_outcome_opened": terminal and evaluated,
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer": terminal and evaluated,
            "network_model_search_fetch_or_evaluator_api_called_by_consumer": False,
            "policy_value_gate2a_evaluated": evaluated,
            "policy_value_gate2a_passed": terminal and evaluated,
            "v24190_authoritative_for_controller_design": False,
            "controller_design_allowed": terminal and evaluated,
            "controller_implementation_or_pilot_launch_allowed": False,
            "training_credit_allowed": False,
            "full220_controller_launch_allowed": False,
            "benchmark_or_sota_claim": False,
        }
        (root / "outputs/v24191_policy_value_gate2a_consumer_state_v1_20260730.json").write_text(
            json.dumps(parent), encoding="utf-8"
        )

    def test_preterminal_wait_does_not_open_scientific_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._parent(root)
            with mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._evaluate"
            ) as evaluate:
                value = run_once(root)
            evaluate.assert_not_called()
            self.assertFalse(value["manifest_model_prediction_or_outcome_opened"])
            self.assertFalse(value["abstain_aware_gate2a_evaluated"])
            self.assertFalse(value["controller_design_allowed"])
            self.assertFalse((root / "results").exists())

    def test_unknown_preterminal_parent_envelope_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._parent(root)
            parent_path = root / "outputs/v24191_policy_value_gate2a_consumer_state_v1_20260730.json"
            parent = json.loads(parent_path.read_text(encoding="utf-8"))
            parent["status"] = "unknown_wait"
            parent_path.write_text(json.dumps(parent), encoding="utf-8")
            with mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._evaluate"
            ) as evaluate:
                with self.assertRaisesRegex(RuntimeError, "waiting envelope"):
                    run_once(root)
            evaluate.assert_not_called()

    def test_parent_terminal_without_report_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._parent(root, terminal=True, evaluated=False)
            with mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._evaluate"
            ) as evaluate:
                with self.assertRaisesRegex(RuntimeError, "lacks policy-value"):
                    run_once(root)
            evaluate.assert_not_called()

    def test_terminal_parent_requires_activation_before_opening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._parent(root, terminal=True, evaluated=True)
            with mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._activation_ready",
                return_value=False,
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24192_abstain_aware_gate2a._evaluate"
            ) as evaluate:
                with self.assertRaisesRegex(RuntimeError, "requires prior activation"):
                    run_once(root)
            evaluate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
