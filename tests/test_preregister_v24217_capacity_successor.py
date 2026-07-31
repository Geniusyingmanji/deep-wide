from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24217_capacity_successor import payload_sha256
from scripts import preregister_v24217_capacity_successor as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24217CapacitySuccessorTests(unittest.TestCase):
    def test_protocol_freezes_post_gate_capacity_without_full220(self) -> None:
        parent = {
            "path": str(prereg.PARENT_STATE),
            "status": "waiting_for_v24215_joint_package_terminal",
            "terminal": False,
            "capacity_measurement_allowed": False,
            "contents_emitted": False,
        }
        legacy = {
            "v24194": {"pid": 1, "start_ticks": 2},
            "v24196": {"pid": 3, "start_ticks": 4},
            "execution_activation_reports_and_freezes_absent": True,
        }
        with mock.patch(
            "scripts.preregister_v24217_capacity_successor._present",
            return_value=False,
        ), mock.patch(
            "scripts.preregister_v24217_capacity_successor._parent_wait",
            return_value=parent,
        ), mock.patch(
            "scripts.preregister_v24217_capacity_successor._legacy_boundary",
            return_value=legacy,
        ), mock.patch(
            "scripts.preregister_v24217_capacity_successor._lease_boundary",
            return_value={"active": False},
        ):
            value = prereg.build_protocol(
                ROOT,
                created_at_unix=1,
                require_pristine=False,
                proc_root=Path("/proc"),
            )
        self.assertEqual(
            value["neutral_capacity_contract"]["levels"], [1, 2, 4, 8, 12]
        )
        self.assertEqual(value["neutral_capacity_contract"]["waves_per_level"], 3)
        self.assertTrue(
            value["crash_only_contract"][
                "execution_start_published_before_client_construction_or_api_call"
            ]
        )
        self.assertFalse(value["authorization"]["full220_launch"])
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in prereg.DECISION_FIELDS}),
        )


if __name__ == "__main__":
    unittest.main()
