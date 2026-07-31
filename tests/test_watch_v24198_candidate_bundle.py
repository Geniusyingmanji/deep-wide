from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24198_candidate_bundle import payload_file_sha256
from scripts.preregister_v24198_candidate_bundle import publish_new
from scripts.watch_v24198_candidate_bundle import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "capacity_contract": {"parent_protocol_sha256": "q" * 64},
        "execution": {
            "state_path": "outputs/v24198_candidate_bundle_watcher_state_v1_20260731.json"
        },
    },
}


class WatchV24198CandidateBundleTests(unittest.TestCase):
    @staticmethod
    def _prerequisites(root: Path) -> None:
        for raw in (
            "results/v24196_capacity_ladder_report_v1_20260731.json",
            "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
            "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json",
            "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json",
            "results/v24198_selected_candidate_handoff_v1_20260731.json",
        ):
            path = root / raw
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")

    def _run(self, root: Path, *, activation=None):
        with mock.patch(
            "scripts.watch_v24198_candidate_bundle.ROOT", root
        ), mock.patch(
            "scripts.watch_v24198_candidate_bundle.validate_protocol",
            return_value=VERIFIED,
        ), mock.patch(
            "scripts.watch_v24198_candidate_bundle._activation",
            return_value=activation,
        ):
            return run_cycle(root, now=1)

    def test_missing_activation_opens_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._run(Path(directory))
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["capacity_pair_opened"])
        self.assertFalse(value["selector_protocol_opened"])
        self.assertFalse(value["candidate_bundle_created"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_activated_pre_capacity_does_not_open_selector(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selector = root / "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json"
            selector.parent.mkdir(parents=True)
            selector.write_text("not-json", encoding="utf-8")
            value = self._run(root, activation={"sha256": "a" * 64})
        self.assertEqual(value["status"], "waiting_for_capacity_freeze")
        self.assertFalse(value["selector_protocol_opened"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_capacity_then_requires_selector_terminal_and_handoff_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for raw in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
            ):
                path = root / raw
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            with mock.patch(
                "scripts.watch_v24198_candidate_bundle.ROOT", root
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle.load_capacity_pair",
                return_value=(
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ):
                first = run_cycle(root, now=1)
                self.assertEqual(first["status"], "waiting_for_selector_preregistration")
                selector = root / "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json"
                selector.write_text("opaque", encoding="utf-8")
                second = run_cycle(root, now=2)
                self.assertEqual(
                    second["status"], "waiting_for_quality_chain_terminal_selection"
                )
                terminal = root / "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json"
                terminal.write_text("opaque", encoding="utf-8")
                third = run_cycle(root, now=3)
                self.assertEqual(third["status"], "waiting_for_selected_candidate_handoff")
        self.assertFalse(third["selector_protocol_opened"])

    def test_bootstrap_validates_in_place_without_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24198_candidate_bundle.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("os.execve", source)
        self.assertIn("V2.41.98 watcher requires python -I -B", source)
        self.assertIn("V2.41.98 control bytes drifted", source)

    def test_bundle_without_go_is_rejected_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for raw in (
                "results/v24196_capacity_ladder_report_v1_20260731.json",
                "results/v24196_next_fresh_all220_capacity_freeze_v1_20260731.json",
                "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json",
                "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json",
                "results/v24198_selected_candidate_handoff_v1_20260731.json",
                "results/v24197_fresh_all220_execution_bundle_v1_20260731.json",
            ):
                path = root / raw
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            selected = {
                "target_name": "x",
                "pipeline_version": "v",
                "state_schema_version": 1,
                "candidate_method_contract_sha256": "d" * 64,
                "model": {},
                "shards": {},
            }
            go = {"benchmark_forward_launch_allowed": False}
            bundle = {"full220_launch_allowed": False}
            with mock.patch(
                "scripts.watch_v24198_candidate_bundle.ROOT", root
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle.load_capacity_pair",
                return_value=(
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ), mock.patch(
                "scripts.watch_v24198_candidate_bundle._compile",
                return_value=(
                    selected,
                    go,
                    bundle,
                    {"selected": 4, "workers": 2, "shards": 2},
                    {},
                    {"report_sha256": "r" * 64, "freeze_sha256": "f" * 64},
                ),
            ), self.assertRaisesRegex(RuntimeError, "before GO"):
                run_cycle(root, now=1)

    def test_transaction_publishes_go_then_bundle_without_launch_authority(self) -> None:
        for recover in (False, True):
            with self.subTest(recover=recover), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._prerequisites(root)
                selected = {
                    "target_name": "fresh",
                    "pipeline_version": "v.future",
                    "state_schema_version": 99,
                    "candidate_method_contract_sha256": "d" * 64,
                }
                go = {
                    "role": "safe_go",
                    "benchmark_forward_launch_allowed": False,
                }
                bundle = {
                    "role": "safe_bundle",
                    "full220_launch_allowed": False,
                }
                capacity = {"selected": 4, "workers": 2, "shards": 2}
                snapshots = {
                    "report_sha256": "r" * 64,
                    "freeze_sha256": "f" * 64,
                }
                if recover:
                    publish_new(
                        root / "results/v24198_candidate_quality_go_receipt_v1_20260731.json",
                        go,
                    )
                with mock.patch(
                    "scripts.watch_v24198_candidate_bundle.ROOT", root
                ), mock.patch(
                    "scripts.watch_v24198_candidate_bundle.validate_protocol",
                    return_value=VERIFIED,
                ), mock.patch(
                    "scripts.watch_v24198_candidate_bundle._activation",
                    return_value={"sha256": "a" * 64},
                ), mock.patch(
                    "scripts.watch_v24198_candidate_bundle.load_capacity_pair",
                    return_value=(capacity, {}, snapshots),
                ), mock.patch(
                    "scripts.watch_v24198_candidate_bundle._compile",
                    return_value=(selected, go, bundle, capacity, {}, snapshots),
                ), mock.patch(
                    "scripts.watch_v24198_candidate_bundle.validate_published_outputs",
                    return_value=selected,
                ):
                    value = run_cycle(root, now=1)
                go_path = root / "results/v24198_candidate_quality_go_receipt_v1_20260731.json"
                bundle_path = root / "results/v24197_fresh_all220_execution_bundle_v1_20260731.json"
                self.assertEqual(
                    __import__("hashlib").sha256(go_path.read_bytes()).hexdigest(),
                    payload_file_sha256(go),
                )
                self.assertEqual(json.loads(bundle_path.read_text()), bundle)
                self.assertEqual(value["status"], "complete_candidate_bundle_frozen")
                self.assertTrue(value["go_receipt_created"])
                self.assertTrue(value["candidate_bundle_created"])
                self.assertFalse(value["candidate_selection_or_gate_evaluated"])
                self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
