from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24210_search_component import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


class WatchV24210SearchComponentTests(unittest.TestCase):
    def test_missing_activation_opens_no_parent_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch("scripts.watch_v24210_search_component.ROOT", root), mock.patch(
                "scripts.watch_v24210_search_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24210_search_component._activation", return_value=None
            ), mock.patch(
                "scripts.watch_v24210_search_component._scope_parent_state"
            ) as scope, mock.patch(
                "scripts.watch_v24210_search_component._search_quality_state"
            ) as quality:
                value = run_cycle(root, now=1)
        scope.assert_not_called()
        quality.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")

    def test_dual_preterminal_opens_no_selected_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch("scripts.watch_v24210_search_component.ROOT", root), mock.patch(
                "scripts.watch_v24210_search_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24210_search_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24210_search_component._scope_parent_state",
                return_value=({"status": "waiting_for_v24206_terminal_markdown_publication"}, False),
            ), mock.patch(
                "scripts.watch_v24210_search_component._search_quality_state",
                return_value=({"status": "waiting_for_schema77_paired_dev_terminal"}, False),
            ), mock.patch(
                "scripts.watch_v24210_search_component.load_inputs"
            ) as loader:
                value = run_cycle(root, now=1)
        loader.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_scope_and_search_quality_terminal")
        self.assertFalse(value["selected_work_order_opened"])
        self.assertFalse(value["search_gate_opened"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_terminal_no_go_retires_without_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            order = {"decision_sha256": "d" * 64}
            publication = {
                "role": "v24210_selected_search_component_publication",
                "publication_disposition": "quality_no_go_component_retired",
                "component_publication": None,
                "search_component_published": False,
                "search_component_retired": True,
                "search_component_absent_noop": False,
                "p12_scope_schema70_parent_preserved": False,
                "mainline_scope_zero_byte_alias_preserved": False,
            }
            with mock.patch("scripts.watch_v24210_search_component.ROOT", root), mock.patch(
                "scripts.watch_v24210_search_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24210_search_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24210_search_component._scope_parent_state",
                return_value=({"status": "complete_mainline_scope_namespace_alias"}, True),
            ), mock.patch(
                "scripts.watch_v24210_search_component._search_quality_state",
                return_value=({"status": "complete_search_yield_no_go"}, True),
            ), mock.patch(
                "scripts.watch_v24210_search_component.load_inputs",
                return_value=({"selected_payload_sha256": "s" * 64}, order, {}, {}),
            ), mock.patch(
                "scripts.watch_v24210_search_component.validate_search_terminal",
                return_value=(
                    "complete_search_yield_no_go",
                    {"status": "complete_search_yield_no_go"},
                    {"passed": False},
                ),
            ), mock.patch(
                "scripts.watch_v24210_search_component._existing_publication",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24210_search_component.build_selected_publication",
                return_value=publication,
            ), mock.patch(
                "scripts.watch_v24210_search_component.publish_new"
            ), mock.patch(
                "scripts.watch_v24210_search_component.hashlib.sha256"
            ) as digest:
                digest.return_value.hexdigest.return_value = "f" * 64
                with mock.patch.object(Path, "read_bytes", return_value=b"x"):
                    value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "complete_search_component_retired_no_go")
        self.assertTrue(value["search_component_retired"])
        self.assertFalse(value["candidate_materialized"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/watch_v24210_search_component.py"
        ).read_text()
        self.assertIn("V2.42.10 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
