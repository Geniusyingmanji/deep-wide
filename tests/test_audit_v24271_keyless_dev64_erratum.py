from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_v24271_keyless_dev64_erratum as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class AuditV24271KeylessDev64ErratumTests(unittest.TestCase):
    def test_real_completed_result_passes_without_network_or_process_mutation(self) -> None:
        with mock.patch.object(target, "process_snapshot", return_value=[]), mock.patch.object(
            target, "lease_observation", return_value={"active": False}
        ):
            value = target.build_report(ROOT, now=1)
        target.validate_report(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["result"]["selected_per_arm"], 64)
        self.assertFalse(value["source_policy"]["old_evaluator_rows_reused"])
        self.assertFalse(value["authorization"]["new_exact220_launch"])

    def test_active_process_or_lease_fails_closed(self) -> None:
        fake_rows = [{"cmd": target.RUNNER_MARKER}]
        with mock.patch.object(target, "process_snapshot", return_value=fake_rows), mock.patch.object(
            target, "_matching", side_effect=lambda rows, marker: rows if marker == target.RUNNER_MARKER else []
        ), mock.patch.object(
            target, "lease_observation", return_value={"active": True}
        ), self.assertRaisesRegex(RuntimeError, "audit drifted"):
            target.build_report(ROOT, now=1)

    def test_tampered_source_policy_or_seal_is_rejected(self) -> None:
        with mock.patch.object(target, "process_snapshot", return_value=[]), mock.patch.object(
            target, "lease_observation", return_value={"active": False}
        ):
            value = target.build_report(ROOT, now=1)
        for mutation in ("source", "seal"):
            altered = copy.deepcopy(value)
            if mutation == "source":
                altered["source_policy"]["old_evaluator_rows_reused"] = True
                unsigned = dict(altered)
                unsigned.pop("audit_payload_sha256")
                altered["audit_payload_sha256"] = payload_sha256(unsigned)
            else:
                altered["audit_payload_sha256"] = "0" * 64
            with self.assertRaisesRegex(RuntimeError, "audit drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
