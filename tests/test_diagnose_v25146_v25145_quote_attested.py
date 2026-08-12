from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25145_quote_attested_external_contract as contract  # noqa: E402
from scripts import diagnose_v25146_v25145_quote_attested as target  # noqa: E402


class V25146DiagnosisTests(unittest.TestCase):
    def test_counts_only_quote_edit_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["verified_gain_tasks"], 7)
        self.assertEqual(funnel["cell_edit_revision_tasks"], 7)
        self.assertEqual(funnel["strict_json_tasks"], 7)
        self.assertEqual(funnel["projection_valid_tasks"], 7)
        self.assertEqual(funnel["model_edit_count_histogram"], {"0": 7})
        self.assertEqual(funnel["model_edit_total"], 0)
        self.assertEqual(funnel["rejected_edit_total"], 0)
        self.assertEqual(funnel["final_prediction_changed_tasks"], 0)

    def test_scanner_decodes_only_two_content_free_receipts_and_booleans(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        value = target.safe_row(line)
        self.assertEqual(set(value), {"outer", "inner"})
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("predictions", encoded)
        self.assertNotIn(contract.task_vector()[0]["opaque_id"], encoded)
        self.assertNotIn("https://", encoded)

    def test_parent_hashes_and_evaluator_barrier_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            value["parents"]["failed_checks"],
            [
                "minimum_attributable_prediction_changed",
                "minimum_quote_attested_projection_applied",
            ],
        )
        self.assertTrue(all(target._absent(path) for path in target.FUTURE_SURFACES))
        self.assertFalse(value["authorization"]["v25145_evaluator_or_quality_result"])

    def test_resealed_funnel_credit_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("funnel", "credit", "launch", "quality"):
            changed = copy.deepcopy(value)
            if kind == "funnel":
                changed["content_free_funnel"]["model_edit_total"] = 1
            elif kind == "credit":
                changed["diagnosis"][
                    "entropy_or_information_gain_signed_credit"
                ] = 1
            elif kind == "launch":
                changed["authorization"]["new_external_protocol_or_launch"] = True
            else:
                changed["authorization"]["v25145_evaluator_or_quality_result"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
