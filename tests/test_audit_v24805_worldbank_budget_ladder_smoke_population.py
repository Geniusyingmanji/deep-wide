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

from scripts import (  # noqa: E402
    audit_v24805_worldbank_budget_ladder_smoke_population as target,
)


class V24805PopulationAuditTests(unittest.TestCase):
    def test_parent_and_historical_exclusion_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        excluded, manifest = target.design.historical_iso3(ROOT)
        self.assertEqual(len(excluded), 96)
        self.assertEqual(len(manifest), 4)

    def test_published_audit_is_narrow_when_present(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.05 population audit not published")
        value = json.loads(path.read_text(encoding="utf-8"))
        target.validate_audit(value)
        self.assertTrue(value["authorization"]["one_smoke_population_publication"])
        self.assertFalse(value["authorization"]["smoke_launch"])
        self.assertFalse(value["authorization"]["evaluator_access"])

    def test_resealed_launch_tamper_fails(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.05 population audit not published")
        value = json.loads(path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(value)
        changed["authorization"]["smoke_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
