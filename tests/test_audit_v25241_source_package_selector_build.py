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

from scripts import audit_v25241_source_package_selector_build as target  # noqa: E402


class V25241SourcePackageSelectorBuildAuditTests(unittest.TestCase):
    def test_fixed_selector_test_design_and_shadow_hashes_match(self) -> None:
        self.assertTrue(target._fixed_hash_barrier())
        self.assertEqual(target._fixed_hashes(), {str(path): expected for path, expected in target.FIXED_HASHES.items()})

    def test_entity_disjoint_design_and_shadow_authority_is_bound(self) -> None:
        self.assertTrue(target._authority_barrier())

    def test_process_capability_is_exact_bounded_and_shell_free(self) -> None:
        capability = target._process_capability_audit()
        self.assertEqual(capability["process_call_count"], 3)
        self.assertTrue(capability["all_process_methods_are_subprocess_run"])
        self.assertEqual(capability["shell_true_lines"], [])
        self.assertEqual(capability["forbidden_network_model_imports"], [])
        self.assertEqual(capability["privileged_runtime_field_accesses"], [])
        self.assertEqual(capability["history_worker_cap"], 16)
        self.assertEqual(capability["whole_selection_wall_ceiling_seconds"], 240)

    def test_fixed_vectors_and_suite_total(self) -> None:
        capability = target._process_capability_audit()
        self.assertEqual(capability["fixed_dpkg_argument_vector"], list(target.selector.DPKG_ARGUMENT_VECTOR))
        self.assertEqual(capability["fixed_history_paths"], list(target.selector.HISTORY_PATHS))
        self.assertEqual(target.EXPECTED_TESTS, 60)

    @staticmethod
    def _mocked_audit() -> dict:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }

        def same(*args: str) -> str:
            return "same" if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")} else ""

        with mock.patch.object(target.base, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            target.base,
            "_watchers",
            return_value={str(pid): {"matches_frozen_identity": True} for pid in target.base.PROTECTED_WATCHERS},
        ), mock.patch.object(target.base, "_lease_inactive", return_value=True), mock.patch.object(
            target.base, "_tracked", return_value=True
        ):
            return target.build_audit(now=1, tracked=False)

    def test_fully_mocked_clean_build_validates(self) -> None:
        value = self._mocked_audit()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["single_source_package_population_freeze"])
        self.assertFalse(value["authorization"]["shadow_external_activation_or_launch"])

    def test_resealed_authority_test_process_runtime_or_credit_tamper_fails(self) -> None:
        value = self._mocked_audit()
        for kind in ("authority", "test", "process", "runtime", "credit"):
            changed = copy.deepcopy(value)
            if kind == "authority":
                changed["authorization"]["shadow_external_activation_or_launch"] = True
            elif kind == "test":
                changed["tests"]["observed"] -= 1
            elif kind == "process":
                changed["process_capability_audit"]["shell_true_lines"] = [1]
            elif kind == "runtime":
                changed["runtime_state"]["attempt_and_result_surfaces_pristine"] = False
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_build_audit_does_not_call_formal_selector_effects(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("_read_source_packages()", source)
        self.assertNotIn("_scan_history(", source)
        self.assertNotIn("selector.execute(", source)


if __name__ == "__main__":
    unittest.main()
