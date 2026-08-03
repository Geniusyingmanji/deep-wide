from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24309_neutral_runner_exit_integration as target  # noqa: E402


class V24309NeutralRunnerExitIntegrationTests(unittest.TestCase):
    def test_real_runner_integration_distinguishes_every_mode(self) -> None:
        receipts = {}
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            for mode in target.MODES:
                directory = base / mode
                directory.mkdir()
                receipts[mode] = target.run_mode(ROOT, mode, directory, 0.15)
                self.assertTrue((directory / "parent_exit_receipt.json").is_file())
        value = target.project(receipts, now=1)
        self.assertEqual(value["observed_taxonomy"], target.EXPECTED)
        self.assertEqual(value["parent_receipt_files_created"], len(target.MODES))
        self.assertFalse(any(value["effect_ledger"].values()))

    def test_protocol_binds_frozen_parent_bytes_and_grants_no_launch(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        target.validate_protocol(ROOT, value)
        self.assertEqual(value["frozen_v24306_sha256"], target.FROZEN_V24306)
        self.assertFalse(value["authorization"]["future_paired_dev64_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_protocol_resealed_extra_field_fails_closed(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["extra"] = "not allowed"
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "protocol drifted"):
            target.validate_protocol(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
