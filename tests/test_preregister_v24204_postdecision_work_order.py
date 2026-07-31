from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24204_postdecision_work_order import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24204PostdecisionWorkOrderTests(unittest.TestCase):
    def test_protocol_predeclares_work_orders_without_build_or_launch(self) -> None:
        with mock.patch(
            "scripts.preregister_v24204_postdecision_work_order.protected_processes",
            return_value={},
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        contract = value["work_order_contract"]
        self.assertEqual(contract["summary"]["decision_count"], 36)
        self.assertEqual(contract["summary"]["identity_handoff_ready_count"], 3)
        self.assertEqual(
            contract["summary"]["blocked_nonempty_work_order_count"], 33
        )
        self.assertTrue(contract["selection_frozen_before_parent_outcome"])
        self.assertTrue(
            contract["terminal_decision_must_be_content_addressed_to_frozen_manifest"]
        )
        self.assertFalse(
            value["authorization"][
                "candidate_code_build_merge_materialization_or_freeze_generation"
            ]
        )
        self.assertFalse(value["authorization"]["component_implementation_publisher"])
        self.assertFalse(value["authorization"]["package_gate_evaluation_or_launch"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in DECISION_FIELDS}),
        )

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
