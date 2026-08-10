from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25028_clue_evaluation_recovery_contract as contract  # noqa: E402
from scripts import recover_v25028_clue_evaluation as target  # noqa: E402


class ClueEvaluationRecoveryTests(unittest.TestCase):
    def test_source_policy_is_zero_network_fixed_denominator(self) -> None:
        policy = contract.source_policy()
        self.assertFalse(policy["network_model_search_fetch_or_forward_effect"])
        self.assertFalse(policy["gold_refetch"])
        self.assertTrue(policy["all_twenty_tasks_and_both_arms_evaluated_once"])
        self.assertEqual(policy["original_failed_attempt_evaluated_prediction_rows"], 0)

    def test_protocol_binds_all_frozen_inputs(self) -> None:
        value = contract.build_protocol(ROOT, now=123, tracked=False)
        checked = contract.validate_protocol(ROOT, value, tracked=False)
        self.assertEqual(checked, value)
        self.assertEqual(len(value["frozen_input_manifest"]), 7)
        self.assertTrue(value["authorization"]["one_read_only_recovery_evaluation"])
        self.assertFalse(value["authorization"]["network_or_gold_refetch"])

    def test_jsonl_reader_requires_all_twenty_rows(self) -> None:
        original = contract.FROZEN_ROWS
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            relative = Path(raw).relative_to(ROOT) / "rows.jsonl"
            path = ROOT / relative
            path.write_text("{}\n" * 19, encoding="utf-8")
            contract.FROZEN_ROWS = relative
            try:
                with self.assertRaises(RuntimeError):
                    target._read_jsonl(relative)
            finally:
                contract.FROZEN_ROWS = original

    def test_failure_receipt_says_zero_metrics_and_no_refetch(self) -> None:
        value = json.loads((ROOT / contract.FAILURE).read_text(encoding="utf-8"))
        self.assertEqual(value["prediction_metric_rows_evaluated"], 0)
        self.assertFalse(value["gold_refetch_allowed"])
        self.assertFalse(value["quality_result_created"])

    def test_recovery_module_has_no_network_or_process_import(self) -> None:
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in ("requests", "socket", "subprocess", "urllib", "deepwidebench"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        self.assertNotIn("requests.get", source)
        self.assertNotIn("acquire_deepwide_api_lease", source)


if __name__ == "__main__":
    unittest.main()
