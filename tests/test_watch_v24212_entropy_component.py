from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24212_entropy_component import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


class WatchV24212EntropyComponentTests(unittest.TestCase):
    def test_missing_activation_opens_no_parent_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24212_entropy_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._search_parent_state"
            ) as search, mock.patch(
                "scripts.watch_v24212_entropy_component._gate2a_state"
            ) as gate:
                value = run_cycle(root, now=1)
        search.assert_not_called()
        gate.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")

    def test_dual_preterminal_opens_no_selected_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24212_entropy_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._search_parent_state",
                return_value=({"status": "waiting_search"}, False),
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._gate2a_state",
                return_value=({"status": "waiting_gate"}, False),
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.load_selected_inputs"
            ) as loader:
                value = run_cycle(root, now=1)
        loader.assert_not_called()
        self.assertEqual(
            value["status"], "waiting_for_search_parent_and_gate2a_terminal"
        )
        self.assertFalse(value["selected_work_order_opened"])
        self.assertFalse(value["gate2a_report_opened"])
        self.assertFalse(value["action_model_opened"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_terminal_no_entropy_publishes_noop_without_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = {
                "selected_work_order": {"decision_sha256": "d" * 64}
            }
            publication = {
                "publication_disposition": "entropy_component_absent_no_op",
                "component_publication": None,
                "entropy_component_published": False,
                "entropy_component_absent_noop": True,
                "real_state_transition_adapters_included": False,
                "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency": False,
            }
            with mock.patch(
                "scripts.watch_v24212_entropy_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._search_parent_state",
                return_value=({"status": "complete_search"}, True),
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._gate2a_state",
                return_value=({"status": "replicate_aware_gate2a_fail"}, True),
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.load_selected_inputs",
                return_value=(selected, None, {}, {}, {}, {}),
            ), mock.patch(
                "scripts.watch_v24212_entropy_component._existing_publication",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.build_selected_publication",
                return_value=publication,
            ), mock.patch(
                "scripts.watch_v24212_entropy_component.publish_new"
            ):
                with mock.patch.object(Path, "read_bytes", return_value=b"x"):
                    value = run_cycle(root, now=1)
        self.assertTrue(value["terminal"])
        self.assertEqual(value["status"], "complete_no_entropy_component_selected")
        self.assertTrue(value["entropy_component_absent_noop"])
        self.assertFalse(value["candidate_materialized"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24212_entropy_component.py"
        ).read_text()
        self.assertIn("V2.42.12 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
