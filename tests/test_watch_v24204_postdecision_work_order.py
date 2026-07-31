from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24204_postdecision_work_order import run_cycle


VERIFIED = {
    "sha256": "p" * 64,
    "value": {
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
    },
}


def work_order(identity: bool) -> dict[str, object]:
    return {
        "identity_handoff_only": identity,
        "disposition": (
            "byte_exact_baseline_identity_handoff_ready"
            if identity
            else "blocked_pending_selected_baseline_publications_and_joint_audit"
        ),
    }


class WatchV24204PostdecisionWorkOrderTests(unittest.TestCase):
    def test_missing_activation_opens_no_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                "scripts.watch_v24204_postdecision_work_order.ROOT", root
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._activation",
                return_value=None,
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._parent_state"
            ) as parent:
                value = run_cycle(root, now=1)
        parent.assert_not_called()
        self.assertEqual(value["status"], "waiting_for_execution_activation")
        self.assertFalse(value["parent_safe_state_envelope_opened"])
        self.assertFalse(value["parent_content_free_decision_receipt_opened"])

    def test_preterminal_parent_never_opens_decision_even_if_path_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "results").mkdir()
            (root / "results/v24200_hierarchical_successor_decision_v1_20260731.json").write_text(
                "not-json"
            )
            parent_state = {"status": "waiting_for_quality_chain_terminal"}
            with mock.patch(
                "scripts.watch_v24204_postdecision_work_order.ROOT", root
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._parent_state",
                return_value=(parent_state, False),
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._parent_decision"
            ) as decision:
                value = run_cycle(root, now=1)
        decision.assert_not_called()
        self.assertEqual(
            value["reason"],
            "parent_decision_path_present_waiting_for_terminal_state_commit",
        )
        self.assertFalse(value["parent_content_free_decision_receipt_opened"])
        self.assertFalse(value["selected_work_order_published"])

    def _terminal(self, *, identity: bool) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent_path = (
                root
                / "results/v24200_hierarchical_successor_decision_v1_20260731.json"
            )
            parent_path.parent.mkdir()
            parent_path.write_text("{}")
            parent_state = {"status": "complete_hierarchical_successor_decision"}
            receipt = {
                "receipt_payload_sha256": "r" * 64,
                "decision": {"decision_payload_sha256": "d" * 64},
            }
            with mock.patch(
                "scripts.watch_v24204_postdecision_work_order.ROOT", root
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order.validate_protocol",
                return_value=VERIFIED,
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._activation",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._parent_state",
                return_value=(parent_state, True),
            ), mock.patch(
                "scripts.watch_v24204_postdecision_work_order._parent_decision",
                return_value=(receipt, work_order(identity)),
            ):
                return run_cycle(root, now=1)

    def test_terminal_identity_publishes_handoff_only(self) -> None:
        value = self._terminal(identity=True)
        self.assertEqual(value["status"], "complete_identity_handoff_work_order")
        self.assertTrue(value["identity_handoff_selected"])
        self.assertFalse(value["candidate_code_built_merged_or_materialized"])
        self.assertFalse(value["package_gate_evaluated_or_launched"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_terminal_nonempty_publishes_blocked_work_order_only(self) -> None:
        value = self._terminal(identity=False)
        self.assertEqual(
            value["status"], "complete_blocked_nonempty_integration_work_order"
        )
        self.assertTrue(value["nonempty_blocked_work_order_selected"])
        self.assertFalse(value["component_implementation_publisher_invoked"])
        self.assertFalse(value["candidate_code_built_merged_or_materialized"])
        self.assertFalse(value["package_gate_evaluated_or_launched"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_bootstrap_requires_isolated_flags_and_no_reexec(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "scripts/watch_v24204_postdecision_work_order.py"
        ).read_text()
        self.assertIn("V2.42.04 watcher requires python -I -B", source)
        self.assertNotIn("os.execve", source)


if __name__ == "__main__":
    unittest.main()
