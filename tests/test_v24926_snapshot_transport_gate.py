from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import control_v24926_snapshot_transport_gate as gate  # noqa: E402


class V24926SnapshotTransportGateTests(unittest.TestCase):
    def test_four_targets_are_fixed_and_unique(self) -> None:
        self.assertEqual(len(gate.TARGET_KEYS), 4)
        self.assertEqual(len(set(gate.TARGET_KEYS)), 4)

    def test_transport_is_serial_single_attempt(self) -> None:
        self.assertEqual(gate.SOCKET_WALL_SECONDS, 90)
        self.assertEqual(len(gate.URLS), 4)

    def test_validate_accepts_complete_worldbank_shape(self) -> None:
        rows = [
            {
                "countryiso3code": f"{chr(65 + index // 676)}{chr(65 + index // 26 % 26)}{chr(65 + index % 26)}",
                "value": index,
            }
            for index in range(180)
        ]
        records, unique = gate._validate(json.dumps([{}, rows]).encode())
        self.assertEqual(records, 180)
        self.assertEqual(unique, 180)

    def test_validate_rejects_incomplete_response(self) -> None:
        rows = [{"countryiso3code": "AAA", "value": 1}]
        with self.assertRaises(RuntimeError):
            gate._validate(json.dumps([{}, rows]).encode())

    def test_protocol_forbids_quality_and_model_effect(self) -> None:
        self.assertNotIn("evaluate", gate.SOURCE.name)
        self.assertTrue(str(gate.CATALOG).startswith("outputs/v24923_"))


if __name__ == "__main__":
    unittest.main()
