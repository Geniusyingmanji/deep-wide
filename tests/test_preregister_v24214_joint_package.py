from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24210_search_component import publish_new
from scripts.preregister_v24214_joint_package import (
    CONTROL_FILES,
    DECISION_FIELDS,
    build_protocol,
)


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24214JointPackageTests(unittest.TestCase):
    def test_protocol_freezes_all_decisions_without_gate_or_launch(self) -> None:
        with mock.patch(
            "scripts.preregister_v24214_joint_package._validate_parent_receipts_at_freeze"
        ), mock.patch(
            "scripts.preregister_v24214_joint_package._parent_preterminal_state",
            return_value={"status": "waiting", "terminal": False},
        ), mock.patch(
            "scripts.preregister_v24214_joint_package.protected_processes",
            return_value={},
        ):
            value = build_protocol(
                ROOT, created_at_unix=1, require_pristine=False
            )
        contract = value["joint_package_contract"]
        self.assertEqual(contract["summary"]["decision_count"], 36)
        self.assertEqual(contract["summary"]["identity_handoff_count"], 3)
        self.assertEqual(
            contract["summary"]["joint_revalidation_required_count"], 33
        )
        self.assertTrue(contract["single_deepest_cumulative_graph_required"])
        self.assertTrue(contract["component_directory_overlay_forbidden"])
        self.assertFalse(value["authorization"]["package_gate_evaluation_or_launch"])
        self.assertFalse(value["authorization"]["dev64_launch"])
        self.assertFalse(
            value["authorization"]["benchmark_forward_or_full220_launch"]
        )
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
