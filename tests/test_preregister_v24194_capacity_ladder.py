from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.preregister_v24194_capacity_ladder import (
    CONTROL_FILES,
    PROTOCOL_ID,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24194CapacityLadderTests(unittest.TestCase):
    def test_protocol_binds_neutral_ladder_and_wait_only_gate(self) -> None:
        value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        self.assertEqual(value["protocol_id"], PROTOCOL_ID)
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(value["capacity_contract"]["settings"]["levels"], [1, 2, 4, 8, 12])
        self.assertEqual(value["capacity_contract"]["settings"]["waves_per_level"], 3)
        self.assertTrue(value["release_and_priority_gate"]["required_phase_terminal"])
        self.assertFalse(value["authorization"]["future_all220_launch"])
        self.assertFalse(value["source_policy"]["search_fetch_or_evaluator_api_called"])

    def test_parent_drift_fails_closed(self) -> None:
        from unittest import mock

        with mock.patch.dict(
            "scripts.preregister_v24194_capacity_ladder.FROZEN_PARENTS",
            {"scripts/deepwide_api_lease.py": "0" * 64},
            clear=True,
        ), self.assertRaisesRegex(RuntimeError, "drifted"):
            build_protocol(ROOT, created_at_unix=1, require_pristine=False)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
