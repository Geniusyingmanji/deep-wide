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

from scripts import diagnose_v25189_v25187_outer_failure as target  # noqa: E402


class V25189OuterFailureDiagnosisTests(unittest.TestCase):
    def test_live_frozen_diagnosis_binds_root_cause_and_fix(self):
        with mock.patch.object(target, "_git", return_value="clean"):
            value = target.build_diagnosis(now=1, require_clean=False)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["frozen_failure"]["one_based_task_positions"], [3, 17])
        self.assertEqual(
            value["frozen_failure"]["failed_task_effect_vectors_query_fetch_model"],
            [[4, 10, 3], [4, 10, 3]],
        )
        self.assertTrue(
            value["root_cause"]["old_wrapper_rejected_parent_valid_safe_export_fallback"]
        )
        self.assertFalse(value["root_cause"]["mechanism_or_quality_negative_result"])
        self.assertFalse(
            value["authorization"][
                "old_population_retry_resume_skip_replacement_or_selective_rerun"
            ]
        )

    def test_resealed_gate_quality_or_retry_tamper_fails_closed(self):
        with mock.patch.object(target, "_git", return_value="clean"):
            value = target.build_diagnosis(now=1, require_clean=False)
        for parent, field, changed_value in (
            ("frozen_failure", "mechanism_gate_passed", True),
            ("root_cause", "mechanism_or_quality_negative_result", True),
            (
                "authorization",
                "old_population_retry_resume_skip_replacement_or_selective_rerun",
                True,
            ),
        ):
            changed = copy.deepcopy(value)
            changed[parent][field] = changed_value
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(parent=parent, field=field), self.assertRaises(
                RuntimeError
            ):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
