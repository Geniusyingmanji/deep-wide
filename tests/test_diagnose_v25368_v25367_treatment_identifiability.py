from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    diagnose_v25368_v25367_treatment_identifiability as target,
)


class V25368TreatmentIdentifiabilityTests(unittest.TestCase):
    def test_content_free_diagnosis_freezes_nonidentifiability(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        row = value["aggregate"]["row_content_free"]
        forward = value["aggregate"]["forward_content_free"]
        self.assertEqual(forward["verified_field_count_total"], 49)
        self.assertEqual(row["candidate_prompt_changed_tasks"], 16)
        self.assertEqual(
            row["candidate_prompt_changed_prediction_equal_tasks"], 16
        )
        self.assertEqual(row["prediction_changed_tasks"], 0)
        self.assertFalse(
            value["diagnosis"][
                "raw_page_redundancy_and_model_insensitivity_are_distinguishable"
            ]
        )
        self.assertTrue(
            value["authorization"]["changed_safe_matched_intervention_build_only"]
        )

    def test_resealed_identifiability_rerun_or_credit_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("identified", "rerun", "credit"):
            changed = copy.deepcopy(value)
            if kind == "identified":
                changed["diagnosis"][
                    "verified_prefix_has_identified_causal_effect"
                ] = True
            elif kind == "rerun":
                changed["authorization"][
                    "same_population_retry_resume_replay_backfill_replacement_or_evaluator"
                ] = True
            else:
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_source_has_no_network_evaluator_or_process_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import subprocess",
            "from urllib",
            "urlopen(",
            "socket.",
            "Popen(",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
