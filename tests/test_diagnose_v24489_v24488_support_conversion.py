from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24489_v24488_support_conversion as target  # noqa: E402


def _reseal(value: dict) -> dict:
    value.pop("diagnosis_payload_sha256", None)
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


class V24489SupportConversionDiagnosisTests(unittest.TestCase):
    def _report(self) -> dict:
        def git(*args: str) -> str:
            if args == ("status", "--porcelain"):
                return ""
            return "a" * 40

        with (
            patch.object(target.base, "_git", side_effect=git),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            return target.build_report(now=0)

    def test_frozen_content_free_evidence_and_authorization(self) -> None:
        value = self._report()
        target.validate_report(value)
        evidence = value["external_gate_evidence"]
        self.assertEqual(evidence["worker_success_tasks"], 8)
        self.assertEqual(evidence["complete_validation_returned_tasks"], 8)
        self.assertEqual(evidence["support_unreachable_tasks"], 7)
        self.assertGreater(evidence["positive_information_gain_total_nats"], 0)
        self.assertEqual(evidence["decision_credit_total_nats"], 0)
        self.assertTrue(
            value["authorization"][
                "entropy_conditioned_targeted_support_offline_design"
            ]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_successor_is_bounded_and_does_not_relax_thresholds(self) -> None:
        work = self._report()["successor_work_order"]
        self.assertTrue(
            work["preserve_known_unknown_support_posterior_and_margin_thresholds"]
        )
        self.assertEqual(work["maximum_targeted_cells"], 1)
        self.assertEqual(work["maximum_additional_search_batches"], 1)
        self.assertEqual(work["maximum_additional_source_disjoint_fetches"], 3)
        self.assertEqual(work["additional_model_requests"], 0)

    def test_resealed_evidence_finding_or_authorization_tamper_fails(self) -> None:
        value = self._report()
        cases = (
            (
                "false_decision_credit",
                lambda item: item["external_gate_evidence"].__setitem__(
                    "decision_credit_total_nats", 1.0
                ),
            ),
            (
                "threshold_relaxation",
                lambda item: item["root_cause_findings"].__setitem__(
                    "support_posterior_or_margin_threshold_relaxation_supported", True
                ),
            ),
            (
                "external_launch",
                lambda item: item["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(value)
                alter(changed)
                _reseal(changed)
                with self.assertRaises(RuntimeError):
                    target.validate_report(changed)

    def test_bound_runtime_sources_are_label_blind(self) -> None:
        accesses: list[str] = []
        imports: list[str] = []
        for path in target.RUNTIME_SOURCES:
            current_accesses, current_imports = target.base._ast_findings(path)
            accesses.extend(current_accesses)
            imports.extend(current_imports)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
