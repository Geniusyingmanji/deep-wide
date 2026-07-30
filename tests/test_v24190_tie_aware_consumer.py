from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24190_tie_aware_gate2a import (
    CONTROL_FILES,
    ROOT,
    build_protocol,
)
from scripts.watch_v24190_tie_aware_gate2a import run_once


class V24190TieAwareConsumerTests(unittest.TestCase):
    def test_protocol_freezes_tie_aware_scientific_contract(self) -> None:
        value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        self.assertEqual(
            value["protocol_id"],
            "v24190_tie_aware_true_continuation_gate2a_consumer_v1",
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        contract = value["tie_aware_contract"]
        self.assertFalse(contract["action_declaration_order_for_ties"])
        self.assertTrue(contract["paired_full_minus_random_required"])
        self.assertTrue(contract["parent_v24161_v24162_result_diagnostic_only"])
        self.assertFalse(value["authorization"]["training_credit"])
        self.assertFalse(value["authorization"]["full220_controller_launch"])

    def test_live_import_graph_is_canonical(self) -> None:
        code = (
            "import json,sys;"
            f"sys.path.insert(0,{str(ROOT)!r});"
            f"sys.path.insert(0,{str(ROOT / 'src')!r});"
            "from scripts.watch_v24190_tie_aware_gate2a "
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
            identity["tie_aware_evaluator_module"],
            "deepwide_agent.v24190_tie_aware_gate2a",
        )

    @staticmethod
    def _states(root: Path, *, status: str = "waiting_for_p12_trial2_exact220_release") -> None:
        (root / "outputs").mkdir()
        source = {
            "role": "v24159_true_continuation_reachability_state",
            "status": status,
            "terminal": status == "audit_terminal",
            "mapping_or_gold_read": False,
            "evaluator_or_score_read": False,
            "api_or_benchmark_forward_called": False,
            "shared_api_lease_acquired": False,
        }
        parent = {
            "role": "v24162_canonical_gate2a_consumer_state",
            "status": "waiting_for_true_continuation_audit_terminal",
            "strict_gate2a_evaluated": False,
            "manifest_prediction_or_outcome_opened": False,
            "controller_design_allowed": False,
            "terminal": False,
        }
        (root / "outputs/v24159_true_continuation_reachability_state_v1_20260729.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
        (root / "outputs/v24162_canonical_gate2a_consumer_state_v1_20260729.json").write_text(
            json.dumps(parent), encoding="utf-8"
        )

    def test_preterminal_wait_does_not_open_scientific_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._states(root)
            with mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._evaluate"
            ) as evaluate:
                value = run_once(root)
            evaluate.assert_not_called()
            self.assertFalse(value["manifest_prediction_or_outcome_opened"])
            self.assertFalse(value["tie_aware_gate2a_evaluated"])
            self.assertFalse(value["controller_design_allowed"])
            self.assertFalse((root / "results").exists())

    def test_terminal_waits_for_parent_terminal_without_opening_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._states(root, status="audit_terminal")
            with mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._evaluate"
            ) as evaluate:
                value = run_once(root)
            evaluate.assert_not_called()
            self.assertFalse(value["manifest_prediction_or_outcome_opened"])
            self.assertFalse(value["tie_aware_gate2a_evaluated"])

    def test_unknown_source_status_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self._states(root, status="unknown")
            with mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.validate_protocol",
                return_value={
                    "sha256": "a" * 64,
                    "value": {"decision_contract_sha256": "b" * 64},
                },
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._activation_ready",
                return_value=True,
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a.assert_canonical_module_identity",
                return_value={"canonical": True},
            ), mock.patch(
                "scripts.watch_v24190_tie_aware_gate2a._evaluate"
            ) as evaluate:
                with self.assertRaisesRegex(RuntimeError, "unregistered"):
                    run_once(root)
            evaluate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
