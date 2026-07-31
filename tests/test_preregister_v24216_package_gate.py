from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24216_package_gate import payload_sha256
from scripts import preregister_v24216_package_gate as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24216PackageGateTests(unittest.TestCase):
    def test_protocol_freezes_paired_cold_gate_before_capacity(self) -> None:
        with mock.patch(
            "scripts.preregister_v24216_package_gate._future_absent", return_value=True
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._parent_preterminal",
            return_value={
                "path": str(prereg.PARENT_STATE),
                "status": "waiting_for_v24213_entropy_recovery_terminal",
                "terminal": False,
                "publication_absent": True,
                "selected_content_opened": False,
                "contents_emitted": False,
            },
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._parent_receipts", return_value={}
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._r1_boundary",
            return_value={"selected": 220, "terminal": 177},
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._capacity_boundary",
            return_value={
                "v24194_execution_activation_absent": True,
                "v24194_report_and_freeze_absent": True,
                "v24196_report_and_freeze_absent": True,
                "v24196_blocked_by_healthy_legacy_watcher": True,
            },
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._process", return_value={}
        ), mock.patch(
            "scripts.preregister_v24216_package_gate._present", return_value=False
        ):
            value = prereg.build_protocol(
                ROOT,
                created_at_unix=1,
                require_pristine=False,
                proc_root=Path("/proc"),
            )
        paired = value["paired_dev64_contract"]
        self.assertFalse(paired["historical_baseline_result_reuse_default"])
        self.assertTrue(paired["paired_baseline_and_candidate_cold_start_required"])
        self.assertTrue(value["capacity_priority_contract"]["package_gate_precedes_neutral_capacity_measurement"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertEqual(set(value["control_surface"]["manifest"]), set(prereg.CONTROL_FILES))
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in prereg.DECISION_FIELDS}),
        )


if __name__ == "__main__":
    unittest.main()
