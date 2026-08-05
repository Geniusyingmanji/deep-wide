from __future__ import annotations

import concurrent.futures
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24569_serialized_protocol_validator_repair as target  # noqa: E402


class V24569SerializedProtocolValidatorRepairTests(unittest.TestCase):
    def test_real_frozen_protocol_validates_through_repair(self) -> None:
        value = target.validate_protocol()
        self.assertEqual(value["protocol_id"], target.frozen.PROTOCOL_ID)
        self.assertTrue(target.binding_valid())

    def test_eight_way_barrier_serializes_complete_validator_call(self) -> None:
        protocol = target.frozen.validate_protocol()
        barrier = threading.Barrier(8)
        state_lock = threading.Lock()
        active = 0
        maximum_active = 0

        def observed(*args, **kwargs):
            nonlocal active, maximum_active
            with state_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            try:
                time.sleep(0.02)
                return target.frozen.validate_protocol(*args, **kwargs)
            finally:
                with state_lock:
                    active -= 1

        def validate_once(_ordinal: int) -> str:
            barrier.wait(timeout=5)
            return target.validate_protocol(value=protocol)["protocol_id"]

        with (
            patch.object(target, "_FROZEN_VALIDATE_PROTOCOL", side_effect=observed),
            concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool,
        ):
            values = list(pool.map(validate_once, range(8)))
        self.assertEqual(values, [target.frozen.PROTOCOL_ID] * 8)
        self.assertEqual(maximum_active, 1)

    def test_lock_is_reentrant_for_nested_successor_validation(self) -> None:
        protocol = target.frozen.validate_protocol()
        with target.serialized_protocol_validation():
            value = target.validate_protocol(value=protocol)
        self.assertEqual(value["protocol_id"], target.frozen.PROTOCOL_ID)

    def test_exception_releases_lock_for_next_validator(self) -> None:
        with patch.object(
            target,
            "_FROZEN_VALIDATE_PROTOCOL",
            side_effect=RuntimeError("synthetic validator failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic validator failure"):
                target.validate_protocol(value={})
        value = target.validate_protocol()
        self.assertEqual(value["protocol_id"], target.frozen.PROTOCOL_ID)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/v24569_serialized_protocol_validator_repair.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
