from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24826_worldbank_exact_api_transport as target  # noqa: E402


class V24826BuildAuditTests(unittest.TestCase):
    def test_parent_authority_is_valid(self) -> None:
        self.assertTrue(target._parent_valid())

    def test_runtime_and_helper_are_label_blind(self) -> None:
        for relative in (target.RUNTIME, target.HELPER):
            fields, imports = target.ast_findings(relative)
            self.assertEqual(fields, [])
            self.assertEqual(imports, [])

    def test_build_is_valid_and_grants_probe_design_only(self) -> None:
        value = target.build(now=1, require_clean=False, require_tracked=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(
            value["authorization"]["non_evaluation_transport_probe_design"]
        )
        self.assertFalse(value["authorization"]["external_population_or_launch"])
        self.assertFalse(value["authorization"]["public_exact220"])

    def test_resealed_launch_authority_tamper_fails(self) -> None:
        value = target.build(now=1, require_clean=False, require_tracked=False)
        changed = copy.deepcopy(value)
        changed["authorization"]["external_population_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
