from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts import audit_v24275_two_wave_dev64_erratum as target


ROOT = Path(__file__).resolve().parents[1]


class V24275PostresultAuditErratumTests(unittest.TestCase):
    def test_exact_frozen_missing_helper_is_hash_bound(self) -> None:
        value = target.verify_exact_frozen_defect(ROOT)
        self.assertEqual(value["missing_symbol"], "_sealed")
        self.assertEqual(value["definition_count"], 0)
        self.assertEqual(value["call_count"], 1)
        self.assertTrue(value["call_is_inside_sealed_file"])
        self.assertEqual(set(value["bound_artifacts"]), set(target.EXPECTED_HASHES))

    def test_in_memory_helper_builds_clean_original_format_audit(self) -> None:
        value = target.build_postaudit(ROOT)
        target.validate_postaudit(value)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["authorization"]["exact220_design"])

    def test_erratum_rejects_resealed_effect_or_go_tamper(self) -> None:
        post = target.build_postaudit(ROOT)
        # Materialize only in a temporary ordinary file because the erratum
        # binds the byte hash of the original-format audit.
        path = ROOT / target.POSTAUDIT
        existed = path.exists()
        if not existed:
            target.publish_new(path, post)
        try:
            value = target.build_erratum(ROOT, post, now=1)
            target.validate_erratum(value)
            for mutation in ("effect", "go"):
                altered = copy.deepcopy(value)
                if mutation == "effect":
                    altered[
                        "network_model_search_fetch_evaluator_or_api_called_by_erratum"
                    ] = True
                else:
                    altered["result"]["decision_passed"] = True
                altered["erratum_payload_sha256"] = target.payload_sha256(
                    {
                        key: item
                        for key, item in altered.items()
                        if key != "erratum_payload_sha256"
                    }
                )
                with self.assertRaisesRegex(RuntimeError, "erratum drifted"):
                    target.validate_erratum(altered)
        finally:
            if not existed:
                path.unlink()


if __name__ == "__main__":
    unittest.main()
