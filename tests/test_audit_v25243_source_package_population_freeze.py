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

from scripts import audit_v25243_source_package_population_freeze as target  # noqa: E402


class V25243SourcePackagePopulationFreezeAuditTests(unittest.TestCase):
    def test_fixed_claim_population_and_start_hashes_match(self) -> None:
        self.assertEqual(target._fixed_hashes(), {str(path): expected for path, expected in target.FIXED_HASHES.items()})

    def test_frozen_claim_population_and_start_validate(self) -> None:
        claim, population, start = target._load()
        self.assertEqual(claim["selection_parent_commit"], target.EXPECTED_SELECTION_PARENT)
        self.assertEqual(population["selection_parent_commit"], target.EXPECTED_SELECTION_PARENT)
        self.assertEqual(start["role"], "v25242_source_package_population_execution_start")

    def test_semantic_audit_is_label_blind_and_effect_capability_limited(self) -> None:
        semantic = target._semantic_audit()
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["forbidden_network_model_imports"], [])
        self.assertEqual(semantic["selector_subprocess_call_count"], 3)

    @staticmethod
    def _mocked_audit() -> dict:
        with mock.patch.object(
            target.base,
            "_git",
            side_effect=lambda *args: (
                "1f71e7ce545666790bcf3253b44b0a30f85e8bba"
                if args[:2] == ("rev-parse", target.EXPECTED_SELECTION_PARENT + "^")
                else "same"
            ),
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={str(pid): {"matches_frozen_identity": True} for pid in target.base.PROTECTED_WATCHERS},
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True), mock.patch.object(
            target.base, "_tracked", return_value=True
        ):
            return target.build_audit(now=1, tracked=False)

    def test_fully_mocked_audit_validates_and_authorizes_design_only(self) -> None:
        value = self._mocked_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["fresh64_shadow_reliability_protocol_design"])
        self.assertFalse(value["authorization"]["fresh64_shadow_external_activation_or_launch"])

    def test_resealed_receipt_semantic_runtime_launch_or_credit_tamper_fails(self) -> None:
        value = self._mocked_audit()
        for kind in ("receipt", "semantic", "runtime", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "receipt":
                changed["selection_receipt"]["completed_history_candidate_count"] -= 1
            elif kind == "semantic":
                changed["semantic_audit"]["privileged_runtime_field_accesses"] = [{"field": "gold", "line": 1}]
            elif kind == "runtime":
                changed["runtime_state"]["shared_api_lease_inactive"] = False
            elif kind == "launch":
                changed["authorization"]["fresh64_shadow_external_activation_or_launch"] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_audit_source_does_not_emit_task_identity_or_question(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("print(task", source)
        self.assertNotIn("print(package", source)
        self.assertNotIn("task[\"question\"]", source)
        self.assertNotIn("_packages_from_question", source)


if __name__ == "__main__":
    unittest.main()
