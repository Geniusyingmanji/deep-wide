from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25304_worldbank_population_nogo as target  # noqa: E402


class V25304WorldBankPopulationNogoAuditTests(unittest.TestCase):
    def test_fixed_claim_result_start_and_sources_are_exact(self) -> None:
        self.assertEqual(
            target._fixed(),
            {str(path): digest for path, digest in target.EXPECTED_FIXED.items()},
        )

    def test_frozen_claim_and_result_validate_as_zero_provider_no_go(self) -> None:
        claim = target.runner.validate_attempt_claim(
            target.json.loads((ROOT / target.runner.ATTEMPT_CLAIM).read_text())
        )
        result = target.runner.validate_result(
            target.json.loads((ROOT / target.runner.RESULT).read_text())
        )
        self.assertTrue(claim["claim_is_permanent_even_on_crash_or_no_go"])
        self.assertEqual(result["decision"], "no_go")
        self.assertEqual(result["effect_accounting"]["catalog_provider_attempt_count"], 0)
        self.assertEqual(result["effect_accounting"]["target_provider_attempt_count"], 0)
        self.assertFalse(result["effect_accounting"]["public_worldbank_network_or_api_called"])

    def test_audit_authorizes_only_successor_repair_build(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["successor_helper_supervisor_repair_build_only"])
        self.assertFalse(value["authorization"]["v25301_retry_resume_reuse_or_population_recovery"])
        self.assertFalse(value["authorization"]["successor_population_freeze_or_external_forward"])

    def test_resealed_effect_authority_or_hidden_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("effect", "authority", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "effect":
                changed["attempt"]["catalog_provider_attempt_count"] = 1
            elif kind == "authority":
                changed["authorization"]["v25301_retry_resume_reuse_or_population_recovery"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_network_model_or_evaluator_call(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "requests.",
            "urlopen(",
            "invoke_helper(",
            "execute_freeze(",
            "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
