from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import finalize_v24798_exact220 as target  # noqa: E402


class V24798FinalizeTests(unittest.TestCase):
    def test_forward_barrier_is_exact220_and_pre_evaluator(self) -> None:
        value = target._forward_barrier()
        self.assertEqual(len(value["runtime_rows"]), 220)
        self.assertEqual(value["forward"]["terminal_predictions"], 220)
        self.assertFalse(value["forward"]["official_evaluator_called"])
        self.assertFalse(value["freeze"]["mapping_gold_or_evaluator_opened_or_hashed"])

    def test_forward_audit_authorizes_only_postfreeze_protocol(self) -> None:
        value = target.validate_forward_audit(target._read(ROOT / target.FORWARD_AUDIT))
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["authorization"]["postfreeze_exact220_evaluator_protocol"])
        self.assertFalse(value["authorization"]["selective_evaluation_or_revaluation"])

    def test_fixed_32_partitions_cover_exact220_once(self) -> None:
        parts = target.fixed_partitions()
        self.assertEqual(len(parts), 32)
        self.assertEqual(parts[0][0], 0)
        self.assertEqual(parts[-1][1], 220)
        self.assertEqual(sum(end - start for start, end in parts), 220)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(parts, parts[1:])))

    def test_configure_reuses_validated_parallel_evaluator(self) -> None:
        target.configure_evaluator()
        self.assertEqual(target.evaluator.EVALUATOR_WORKERS, 32)
        self.assertEqual(target.evaluator.OUTPUT_ROOT, target.contract.OUTPUT_ROOT)
        self.assertEqual(target.evaluator.RUNTIME_PREDICTIONS, target.contract.RUNTIME_PREDICTIONS)
        self.assertIs(target.evaluator.run_parallel_evaluator, target.evaluator.run_parallel_evaluator)

    def test_group_metrics_are_conservative(self) -> None:
        metric = {"entity_acc": 0.1, "f1_by_row": 0.2, "f1_by_item": 0.3, "column_f1": 0.4, "score": 0.0}
        summary = {"groups": {"all_220": {"selected": 220, "evaluator_valid": 220, "evaluator_invalid_or_not_run": 0, "conservative_all_selected": metric}}, "per_task": [{"evaluator_valid": True, "metrics": {"score": 1.0}}] * 220}
        value = target._group_metrics(summary, "all_220")
        self.assertAlmostEqual(value["quality_composite"], 0.25)
        self.assertEqual(value["whole_table_successes"], 220)

    def test_group_metrics_reject_unknown_group(self) -> None:
        with self.assertRaises(ValueError):
            target._group_metrics({"groups": {}, "per_task": []}, "dev_24")

    def test_result_claims_forbid_sota_avg4_and_selective_retry(self) -> None:
        self.assertFalse(target.RESULT_CLAIMS["sota"])
        self.assertFalse(target.RESULT_CLAIMS["avg_at_4"])
        self.assertFalse(target.RESULT_CLAIMS["leaderboard_submitted"])
        self.assertFalse(target.RESULT_AUTHORIZATION["selective_retry_or_revaluation"])

    def test_postresult_audit_fails_closed_on_any_finding(self) -> None:
        value = {
            "role": "v24798_exact220_postresult_audit",
            "protocol_id": target.contract.PROTOCOL_ID,
            "audit_valid": False,
            "findings": ["bad"],
            "checks": {"bad": False},
            "provenance": {},
            "authorization": dict(target.RESULT_AUTHORIZATION),
        }
        value["audit_payload_sha256"] = target.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError), mock.patch.object(
            target.contract, "sha256", return_value="unused"
        ):
            target.validate_postresult_audit(value)

    def test_create_only_publication_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "x.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError): target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
