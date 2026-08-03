from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_v24290_low_coverage_task_runtime as target  # noqa: E402


class V24290LowCoverageBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_real_report_is_label_blind_static_clean_and_unauthorized(self) -> None:
        target.validate_report(self.value)
        self.assertTrue(self.value["static_audit"]["passed"])
        self.assertEqual(self.value["findings"], [])
        self.assertFalse(any(self.value["authorization"].values()))

    def test_synthetic_replay_is_selective_and_effect_accounted(self) -> None:
        replay = self.value["synthetic_replay"]
        self.assertFalse(replay["stop"]["rescue_triggered"])
        self.assertTrue(replay["low_coverage"]["rescue_triggered"])
        self.assertEqual(replay["low_coverage"]["provider_search_calls_added_by_rescue"], 0)
        self.assertGreater(replay["low_coverage"]["usable_pages_after"], replay["low_coverage"]["usable_pages_before"])
        self.assertLessEqual(replay["low_coverage"]["total_fetches"], 10)

    def test_resealed_authorization_or_static_tamper_is_rejected(self) -> None:
        for mutation in ("launch", "static"):
            altered = copy.deepcopy(self.value)
            if mutation == "launch":
                altered["authorization"]["exact220_launch"] = True
            else:
                altered["static_audit"]["passed"] = False
            altered["audit_payload_sha256"] = target.payload_sha256(
                {key: value for key, value in altered.items() if key != "audit_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "build audit drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
