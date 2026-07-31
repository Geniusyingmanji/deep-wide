from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24196_capacity_executor import (
    CONTROL_FILES,
    LEGACY_CAPACITY_WATCHER_MARKER,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24196CapacityExecutorTests(unittest.TestCase):
    def test_protocol_exactly_inherits_ladder_and_protects_legacy_watcher(self) -> None:
        value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        self.assertEqual(value["capacity_contract"]["settings"]["levels"], [1, 2, 4, 8, 12])
        self.assertEqual(value["capacity_contract"]["settings"]["waves_per_level"], 3)
        self.assertTrue(value["capacity_contract"]["inherited_v24194_contract_exact"])
        self.assertTrue(
            value["release_and_compatibility_gate"][
                "legacy_v24194_watcher_absent_before_lease_required"
            ]
        )
        self.assertEqual(
            value["execution"]["protected_legacy_capacity_watcher_marker"],
            LEGACY_CAPACITY_WATCHER_MARKER,
        )
        self.assertEqual(
            value["release_and_compatibility_gate"]["safe_wait_boundary"][
                "protected_processes"
            ],
            {},
        )
        self.assertFalse(value["authorization"]["future_all220_launch"])
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))

    def test_frozen_evidence_drift_fails_closed(self) -> None:
        with mock.patch.dict(
            "scripts.preregister_v24196_capacity_executor.FROZEN_EVIDENCE",
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
