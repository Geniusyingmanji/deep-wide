from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24200_successor import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


class WatchV24200SuccessorTests(unittest.TestCase):
    def test_missing_activation_opens_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch("scripts.watch_v24200_successor.ROOT", root), mock.patch(
                "scripts.watch_v24200_successor.validate_protocol", return_value=VERIFIED
            ), mock.patch("scripts.watch_v24200_successor._activation", return_value=None):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["source_status_envelopes_opened"])
        self.assertFalse(value["decision_receipt_created"])

    def test_preterminal_statuses_publish_no_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch("scripts.watch_v24200_successor.ROOT", root), mock.patch(
                "scripts.watch_v24200_successor.validate_protocol", return_value=VERIFIED
            ), mock.patch(
                "scripts.watch_v24200_successor._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24200_successor.read_object", return_value={}
            ), mock.patch(
                "scripts.watch_v24200_successor.derive_successor_decision",
                return_value=(None, {"schema76": "waiting"}),
            ):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "waiting_for_quality_chain_terminal")
        self.assertTrue(value["source_status_envelopes_opened"])
        self.assertFalse(value["source_numeric_metrics_reports_predictions_or_aggregates_read"])
        self.assertFalse(value["integrated_package_built_or_opened"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_terminal_decision_still_does_not_build_or_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decision = {
                "baseline_name": "p12",
                "eligible_components": [],
                "decision_payload_sha256": "x" * 64,
            }
            with mock.patch("scripts.watch_v24200_successor.ROOT", root), mock.patch(
                "scripts.watch_v24200_successor.validate_protocol", return_value=VERIFIED
            ), mock.patch(
                "scripts.watch_v24200_successor._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24200_successor.read_object", return_value={}
            ), mock.patch(
                "scripts.watch_v24200_successor.derive_successor_decision",
                return_value=(decision, {"schema76": "no_go"}),
            ):
                value = run_cycle(root, now=1)
        self.assertTrue(value["terminal"])
        self.assertTrue(value["decision_receipt_created"])
        self.assertFalse(value["integrated_package_built_or_opened"])
        self.assertFalse(value["package_gate_evaluated_or_launched"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (Path(__file__).parents[1] / "scripts/watch_v24200_successor.py").read_text()
        self.assertIn("V2.42.00 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
