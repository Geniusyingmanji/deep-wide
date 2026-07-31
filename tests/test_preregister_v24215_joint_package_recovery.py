from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24210_search_component import publish_new
from scripts import preregister_v24215_joint_package_recovery as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24215JointPackageRecoveryTests(unittest.TestCase):
    def test_protocol_freezes_only_path_delta_without_gate_or_launch(self) -> None:
        recovery_parent = prereg._fixed()["recovery_parent"]
        with mock.patch(
            "scripts.preregister_v24215_joint_package_recovery._failed_parent",
            return_value=recovery_parent,
        ), mock.patch(
            "scripts.preregister_v24215_joint_package_recovery._parent_preterminal_state",
            return_value={
                "path": str(prereg.PARENT_STATE),
                "status": "waiting_for_search_parent_and_gate2a_terminal",
                "terminal": False,
                "selected_content_opened": False,
                "contents_emitted": False,
            },
        ), mock.patch(
            "scripts.preregister_v24215_joint_package_recovery._v24214_watcher_pids",
            return_value=[],
        ), mock.patch(
            "scripts.preregister_v24215_joint_package_recovery.protected_processes",
            return_value={},
        ):
            value = prereg.build_protocol(
                ROOT, created_at_unix=1, require_pristine=False
            )
        contract = value["joint_package_contract"]
        self.assertEqual(contract["summary"]["recovery_decision_count"], 36)
        self.assertEqual(contract["summary"]["entropy_path_corrected_count"], 18)
        self.assertEqual(
            contract["summary"]["byte_identical_nonentropy_order_count"], 18
        )
        self.assertEqual(
            contract["failed_path"],
            "results/v24213_selected_entropy_component_recovery_publication_v1_20260731.json",
        )
        self.assertEqual(
            contract["actual_path"],
            "results/v24213_selected_entropy_component_publication_v1_20260731.json",
        )
        self.assertFalse(value["authorization"]["package_gate_evaluation_or_launch"])
        self.assertFalse(value["authorization"]["dev64_launch"])
        self.assertFalse(
            value["authorization"]["benchmark_forward_or_full220_launch"]
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(prereg.CONTROL_FILES))
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in prereg.DECISION_FIELDS}),
        )

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
