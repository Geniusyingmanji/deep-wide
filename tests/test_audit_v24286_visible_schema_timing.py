from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_v24286_visible_schema_timing as target  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


class AuditV24286VisibleSchemaTimingTests(unittest.TestCase):
    def test_real_report_is_label_blind_and_authorizes_nothing(self):
        value = target.build_report(ROOT, now=1)
        target.validate_report(value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(any(value["authorization"].values()))
        self.assertEqual(
            value["evaluator_failure_taxonomy"][
                "official_evaluator_empty_inner_dataframe_bug"
            ],
            11,
        )

    def test_replay_is_aggregate_only_and_static_surface_has_no_privileged_access(self):
        value = target.build_report(ROOT, now=1)
        replay = value["frozen_exact220_mechanical_replay"]
        self.assertEqual(replay["selected"], 220)
        self.assertFalse(replay["question_column_prediction_or_opaque_id_persisted"])
        self.assertEqual(value["static_audit"]["privileged_exact_key_accesses"], [])
        encoded = json.dumps(replay, ensure_ascii=False)
        for forbidden in ("task_", "Product Series", "北京", "Model Name"):
            self.assertNotIn(forbidden, encoded)

    def test_resealed_authority_taxonomy_or_replay_tamper_fails(self):
        for mutation in ("authority", "taxonomy", "replay"):
            altered = copy.deepcopy(target.build_report(ROOT, now=1))
            if mutation == "authority":
                altered["authorization"]["exact220_launch"] = True
            elif mutation == "taxonomy":
                altered["evaluator_failure_taxonomy"][
                    "official_evaluator_empty_inner_dataframe_bug"
                ] -= 1
            else:
                altered["frozen_exact220_mechanical_replay"]["selected"] -= 1
            unsigned = dict(altered)
            unsigned.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = payload_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "audit drifted"):
                target.validate_report(altered)


if __name__ == "__main__":
    unittest.main()
