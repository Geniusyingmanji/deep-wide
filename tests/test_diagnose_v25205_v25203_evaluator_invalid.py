from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25205_v25203_evaluator_invalid as target  # noqa: E402
from deepwide_agent import v25203_post_effect_tolerant_quality_contract as contract  # noqa: E402


class V25205EvaluatorInvalidDiagnosisTests(unittest.TestCase):
    def test_diagnosis_preserves_uncertainty_and_withholds_authority(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertTrue(target.validate_diagnosis(value)["audit_valid"])
        self.assertTrue(
            value["diagnosis"][
                "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
            ]
        )
        self.assertTrue(
            value["diagnosis"][
                "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run"
            ]
        )
        self.assertFalse(
            value["authorization"][
                "same_population_refetch_revalue_retry_resume_or_replacement"
            ]
        )

    def test_resealed_overclaim_or_credit_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("root-cause", "credit"):
            changed = copy.deepcopy(value)
            if kind == "root-cause":
                changed["diagnosis"][
                    "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run"
                ] = False
            else:
                changed["source_policy"][
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            changed = contract.seal(changed, "diagnosis_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
