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

from scripts import (  # noqa: E402
    audit_v25184_v25182_population_typo_correction as target,
)


class V25184PopulationTypoCorrectionTests(unittest.TestCase):
    def test_live_correction_binds_actual_vector_without_reexecution(self):
        with mock.patch.object(target, "_clean_pushed", return_value=("h", "h")):
            value = target.build_audit(
                now=1, require_clean=True, require_pristine=False
            )
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(
            value["correction"]["actual_forward_visible_identity"], "adnuts"
        )
        self.assertEqual(
            value["correction"]["original_mistyped_visible_identity"],
            "adnutes",
        )
        self.assertFalse(
            value["supersession"][
                "completed_v25183_forward_replayed_or_reexecuted"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward_or_evaluator"])

    def test_original_and_correct_vectors_differ_only_at_position_13(self):
        correct = target._normalized(target.CORRECT_IDENTITIES)
        typo = target._normalized(target.TYPO_IDENTITIES)
        differences = [
            index
            for index, pair in enumerate(zip(correct, typo, strict=True), start=1)
            if pair[0] != pair[1]
        ]
        self.assertEqual(differences, [13])
        self.assertEqual(
            target.contract.payload_sha256(correct),
            target.CORRECT_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.contract.payload_sha256(typo),
            target.TYPO_IDENTITY_VECTOR_SHA256,
        )

    def test_resealed_quality_credit_or_rerun_tamper_fails_closed(self):
        with mock.patch.object(target, "_clean_pushed", return_value=("h", "h")):
            value = target.build_audit(
                now=1, require_clean=True, require_pristine=False
            )
        mutations = (
            ("source_policy", "entropy_or_information_gain_assigns_signed_credit"),
            ("supersession", "completed_v25183_forward_replayed_or_reexecuted"),
            ("supersession", "v25183_quality_effect_established"),
            ("authorization", "external_forward_or_evaluator"),
        )
        for parent, field in mutations:
            changed = copy.deepcopy(value)
            changed[parent][field] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(parent=parent, field=field), self.assertRaises(
                RuntimeError
            ):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
