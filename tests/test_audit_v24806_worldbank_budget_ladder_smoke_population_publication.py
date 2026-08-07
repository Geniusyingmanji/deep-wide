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
    audit_v24806_worldbank_budget_ladder_smoke_population_publication as target,
)


class V24806PublicationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_population_denominator_and_strata(self) -> None:
        self.assertEqual(self.value["counts"], {
            "tasks": 16,
            "countries": 64,
            "unique_country_iso3": 64,
            "strata": {"complete": 10, "missing": 4, "mixed": 2},
        })

    def test_public_surface_excludes_private_identity_and_gold(self) -> None:
        self.assertTrue(
            self.value["checks"]["public_leaf_values_exclude_identity_and_gold"]
        )
        self.assertTrue(
            self.value["checks"]["private_forbids_forward_import_and_early_evaluator"]
        )

    def test_publication_authorizes_design_only(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["isolated_smoke_protocol_design"])
        self.assertFalse(authorization["smoke_launch"])
        self.assertFalse(authorization["evaluator_access"])
        self.assertFalse(authorization["public_dev64_or_exact220"])

    def test_seal_and_escalation_tamper_rejected(self) -> None:
        target.validate_audit(self.value)
        changed = copy.deepcopy(self.value)
        changed["authorization"]["smoke_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
