from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24207_scope_alias_component import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


class WatchV24207ScopeAliasComponentTests(unittest.TestCase):
    def test_missing_activation_opens_no_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24207_scope_alias_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._parent_state"
            ) as parent:
                value = run_cycle(root, now=1)
        parent.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["parent_safe_state_envelope_opened"])

    def test_preterminal_parent_opens_no_selected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24207_scope_alias_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._parent_state",
                return_value=({"status": "waiting_for_v24204_terminal_work_order"}, False),
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.load_inputs"
            ) as loader:
                value = run_cycle(root, now=1)
        loader.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_v24206_terminal_markdown_publication")
        self.assertFalse(value["parent_selected_work_order_opened"])
        self.assertFalse(value["parent_markdown_publication_opened"])

    def test_terminal_mainline_alias_is_zero_byte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            order = {
                "decision_sha256": "d" * 64,
                "publication_mode": "bind_zero_byte_mainline_scope_namespace_alias",
                "disposition": "schema76_existing_mainline_scope_namespace_alias",
            }
            publication = {
                "role": "v24207_selected_scope_alias_component_publication",
                "branch_scope_component_published": True,
                "component_publication": {"publication_kind": "zero_byte_mainline_scope_namespace_alias"},
            }
            with mock.patch(
                "scripts.watch_v24207_scope_alias_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._parent_state",
                return_value=({"status": "complete_selected_baseline_markdown_rebase"}, True),
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.load_inputs",
                return_value=({"selected_payload_sha256": "s" * 64}, order, {}),
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component._existing_publication",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24207_scope_alias_component.build_selected_publication",
                return_value=publication,
            ):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "complete_mainline_scope_namespace_alias")
        self.assertTrue(value["mainline_zero_byte_namespace_alias_selected"])
        self.assertFalse(value["historical_scope_patch_reapplied"])
        self.assertFalse(value["candidate_bytes_modified_or_materialized"])
        self.assertFalse(value["joint_package_built_or_materialized"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/watch_v24207_scope_alias_component.py"
        ).read_text()
        self.assertIn("V2.42.07 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
