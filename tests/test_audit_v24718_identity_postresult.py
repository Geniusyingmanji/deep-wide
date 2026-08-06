from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24718_identity_postresult as audit  # noqa: E402


class V24718IdentityPostresultAuditTests(unittest.TestCase):
    def test_live_build_is_valid_without_effects(self) -> None:
        value = audit.build_audit(now=0)
        audit.validate_audit(value)
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["new_evaluator_calls"], 0)
        self.assertEqual(value["whole_table_successes"], 7)

    def test_metric_or_evaluator_tamper_fails_validation(self) -> None:
        value = audit.build_audit(now=0)
        for path, replacement in (
            (("metrics_equal_control",), False),
            (("new_evaluator_calls",), 1),
            (("whole_table_successes",), 8),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]] = replacement
            tampered.pop("audit_payload_sha256")
            tampered["audit_payload_sha256"] = audit.contract.payload_sha256(tampered)
            with self.assertRaisesRegex(RuntimeError, "drifted"):
                audit.validate_audit(tampered)


if __name__ == "__main__":
    unittest.main()
