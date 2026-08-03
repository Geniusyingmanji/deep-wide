from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24313_neutral_runner_integration as target  # noqa: E402


class NeutralRunnerIntegrationTests(unittest.TestCase):
    def test_protocol_binds_v24312_and_grants_no_launch(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        target.validate_protocol(ROOT, value)
        self.assertTrue(value["deadline_aware_slot_and_provider"])
        self.assertTrue(value["outer_totality"])
        self.assertFalse(value["authorization"]["fresh_paired_dev64_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_two_real_children_are_terminal_and_zero_external_effect(self) -> None:
        value = target.execute_probe(ROOT)
        target.validate_projection(value)
        self.assertEqual(value["parent_taxonomy"], {arm: "success" for arm in target.MODES})
        self.assertEqual(value["parent_receipts_created"], 2)
        self.assertEqual(value["child_terminal_receipts_created"], 2)
        self.assertFalse(any(value["external_effect_ledger"].values()))
        for case in value["cases"].values():
            self.assertEqual(case["model_effects"], 3)
            self.assertEqual(case["slot_acquisitions"], 3)
            self.assertFalse(case["fourth_model_effect"])

    def test_protocol_source_manifest_tamper_fails_closed(self) -> None:
        value = target.build_protocol(ROOT, now=1)
        altered = json.loads(json.dumps(value))
        altered["source_manifest"][target.SOURCE_FILES[0]] = "0" * 64
        altered["source_manifest_sha256"] = target.payload_sha256(
            altered["source_manifest"]
        )
        altered.pop("protocol_payload_sha256")
        altered["protocol_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "protocol drifted"):
            target.validate_protocol(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
