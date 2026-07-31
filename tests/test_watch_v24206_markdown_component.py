from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24206_markdown_component import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


class WatchV24206MarkdownComponentTests(unittest.TestCase):
    def test_missing_activation_opens_no_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24206_markdown_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24206_markdown_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._parent_state"
            ) as parent:
                value = run_cycle(root, now=1)
        parent.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["parent_selected_work_order_opened"])

    def test_preterminal_parent_never_opens_selected_work_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "results/v24204_selected_postdecision_work_order_v1_20260731.json"
            selected.parent.mkdir()
            selected.write_text("not-json")
            parent_state = {"status": "waiting_for_v24200_terminal_decision"}
            with mock.patch(
                "scripts.watch_v24206_markdown_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24206_markdown_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._parent_state",
                return_value=(parent_state, False),
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._parent_selected"
            ) as selected_reader:
                value = run_cycle(root, now=1)
        selected_reader.assert_not_called()
        self.assertEqual(
            value["reason"],
            "parent_selected_work_order_path_present_waiting_for_terminal_state_commit",
        )
        self.assertFalse(value["parent_selected_work_order_opened"])
        self.assertFalse(value["component_publication_created"])

    def test_terminal_publication_is_selected_baseline_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            order = {
                "decision_sha256": "d" * 64,
                "publication_mode": "materialize_selected_baseline_rebase",
                "disposition": "schema76_selected_baseline_markdown_rebase_publication",
            }
            publication = {
                "role": "v24206_selected_markdown_component_publication",
                "markdown_component_published": True,
                "component_publication": {"target_state_schema_version": 78},
            }
            with mock.patch(
                "scripts.watch_v24206_markdown_component.ROOT", root
            ), mock.patch(
                "scripts.watch_v24206_markdown_component.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._parent_state",
                return_value=({"status": "complete_blocked_nonempty_integration_work_order"}, True),
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._parent_selected",
                return_value=({"selected_payload_sha256": "s" * 64}, order),
            ), mock.patch(
                "scripts.watch_v24206_markdown_component._existing_publication",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24206_markdown_component.build_selected_publication",
                return_value=publication,
            ):
                value = run_cycle(root, now=1)
        self.assertEqual(value["status"], "complete_selected_baseline_markdown_rebase")
        self.assertTrue(value["parent_selected_work_order_opened"])
        self.assertTrue(value["selected_baseline_candidate_materialized"])
        self.assertFalse(value["branch_scope_patch_or_namespace_alias_applied"])
        self.assertFalse(value["search_yield_or_entropy_implemented"])
        self.assertFalse(value["joint_package_built_or_materialized"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/watch_v24206_markdown_component.py"
        ).read_text()
        self.assertIn("V2.42.06 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
