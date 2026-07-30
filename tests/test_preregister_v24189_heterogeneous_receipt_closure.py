from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.preregister_v24189_heterogeneous_receipt_closure import (
    CONTROL_FILES,
    DEFAULT_PROTOCOL,
    DEFAULT_RESULT,
    build_protocol,
    payload_sha,
    validate_protocol,
)


class PreregisterV24189HeterogeneousReceiptClosureTests(unittest.TestCase):
    def test_protocol_records_failed_v24188_and_two_receipt_contracts(self) -> None:
        root = Path(__file__).parents[1]
        with patch(
            "scripts.preregister_v24189_heterogeneous_receipt_closure._parents",
            return_value={},
        ):
            value = build_protocol(
                root, created_at_unix=1, require_pristine_result=False
            )
        self.assertTrue(value["disposition"]["v24188_audit_result_absent"])
        self.assertIn("content-addressed", value["audit_contract"]["v24183_receipt_contract"])
        self.assertIn("receipt_payload_sha256", value["audit_contract"]["v24185_v24186_receipt_contract"])
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["control_surface"]["manifest_sha256"],
            payload_sha(value["control_surface"]["manifest"]),
        )
        self.assertFalse(
            value["authorization"]["v24187_or_v24188_source_or_protocol_modification"]
        )

    def test_live_protocol_rebuilds_when_published(self) -> None:
        root = Path(__file__).parents[1]
        path = root / DEFAULT_PROTOCOL
        if not path.exists():
            self.skipTest("protocol not published yet")
        self.assertEqual(
            validate_protocol(root, path)["value"]["role"],
            "v24189_heterogeneous_receipt_closure_preregistration",
        )

    def test_result_pristine_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in CONTROL_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            result = root / DEFAULT_RESULT
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_text("{}", encoding="utf-8")
            with patch(
                "scripts.preregister_v24189_heterogeneous_receipt_closure._parents",
                return_value={},
            ), self.assertRaises(FileExistsError):
                build_protocol(root, created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
