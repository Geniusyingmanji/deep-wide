from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.watch_v24195_lease_owner_compatibility import _atomic_json, run_once


class WatchV24195LeaseOwnerCompatibilityTests(unittest.TestCase):
    def test_run_once_only_publishes_report(self) -> None:
        report = {
            "role": "v24195_lease_owner_compatibility_audit",
            "overall_status": "healthy",
            "compatibility": {"mode": "parent_authoritative_inactive_lease"},
        }
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            with mock.patch(
                "scripts.watch_v24195_lease_owner_compatibility.validate_protocol"
            ), mock.patch(
                "scripts.watch_v24195_lease_owner_compatibility._target",
                return_value=target,
            ), mock.patch(
                "scripts.watch_v24195_lease_owner_compatibility.build_report",
                return_value=report,
            ):
                value = run_once(Path(directory), state=target, now=1)
            self.assertEqual(value, report)
            self.assertTrue(target.is_file())

    def test_atomic_json_replaces_without_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            _atomic_json(path, {"n": 1})
            _atomic_json(path, {"n": 2})
            self.assertEqual(__import__("json").loads(path.read_text()), {"n": 2})
            self.assertFalse(path.is_symlink())


if __name__ == "__main__":
    unittest.main()
