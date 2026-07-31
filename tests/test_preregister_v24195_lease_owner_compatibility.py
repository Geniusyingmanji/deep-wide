from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24195_lease_owner_compatibility import (
    CONTROL_FILES,
    EXPECTED_PARENT_FINDING,
    REGISTERED_OWNER,
    REGISTERED_PURPOSE,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24195LeaseOwnerCompatibilityTests(unittest.TestCase):
    def test_protocol_registers_one_exact_owner_purpose_without_authority(self) -> None:
        value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        contract = value["compatibility_contract"]
        self.assertEqual(contract["registered_owner"], REGISTERED_OWNER)
        self.assertEqual(contract["registered_purpose"], REGISTERED_PURPOSE)
        self.assertEqual(
            contract["frozen_parent_expected_finding"], EXPECTED_PARENT_FINDING
        )
        self.assertTrue(contract["preserve_all_unrelated_parent_critical_findings"])
        self.assertFalse(value["authorization"]["shared_api_lease_acquire"])
        self.assertFalse(value["authorization"]["execution_activation_publish"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))

    def test_parent_drift_fails_closed(self) -> None:
        with mock.patch.dict(
            "scripts.preregister_v24195_lease_owner_compatibility.FROZEN_PARENTS",
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
