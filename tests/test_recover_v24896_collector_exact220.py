from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import recover_v24896_collector_exact220 as target  # noqa: E402


class V24896CollectorRecoveryExact220Tests(unittest.TestCase):
    def test_fixed_collector_recovers_exactly_163_structural_bundles(self) -> None:
        rows, valid = target.collect_rows()
        self.assertEqual(len(rows), 220)
        self.assertEqual(valid, 163)
        self.assertEqual(len({row["opaque_id"] for row in rows}), 220)

    def test_all_rows_are_label_blind_and_hash_bound(self) -> None:
        rows, _valid = target.collect_rows()
        for row in rows:
            self.assertTrue(row["label_blind"])
            self.assertFalse(
                row["mapping_gold_category_question_type_split_evaluator_score_read"]
            )

    def test_static_runtime_has_no_privileged_or_evaluator_capability(self) -> None:
        path = ROOT / "scripts/recover_v24896_collector_exact220.py"
        self.assertEqual(semantic_audit._accesses(path.resolve(), ROOT), [])
        self.assertEqual(
            semantic_audit._evaluator_capabilities(path.resolve(), ROOT), []
        )

    def test_recovery_has_no_model_search_fetch_or_process_call(self) -> None:
        path = ROOT / "scripts/recover_v24896_collector_exact220.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        recover = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "recover"
        )
        calls = {
            node.func.attr
            for node in ast.walk(recover)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "Popen", "run"}
            )
        )


if __name__ == "__main__":
    unittest.main()
