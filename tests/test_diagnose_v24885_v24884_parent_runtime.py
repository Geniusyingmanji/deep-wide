from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v24885_v24884_parent_runtime as target  # noqa: E402


class V24885ContentFreeParentRuntimeDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = target.summarize()

    def test_exact_frozen_denominator_and_bundle_partition(self) -> None:
        self.assertEqual(self.summary["selected"], 220)
        self.assertEqual(
            self.summary["bundle_commit_marker"], {"absent": 60, "present": 160}
        )

    def test_all_fallbacks_share_one_content_free_terminal_path(self) -> None:
        self.assertEqual(
            self.summary["child_exception_type_counts"],
            {"ValidationError": 60, "none": 160},
        )
        self.assertEqual(
            self.summary["mapping_recovery_stage_counts"],
            {"bundle_committed": 160, "parent_runtime_entered": 60},
        )
        conclusion = self.summary["mechanical_conclusion"]
        self.assertTrue(conclusion["all_fallbacks_same_terminal_path"])
        self.assertEqual(conclusion["fallbacks_reaching_parent_runtime_returned"], 0)

    def test_fallbacks_completed_parent_effect_progress(self) -> None:
        progress = self.summary["safe_progress"]
        self.assertEqual(
            progress["admitted_model_call_distribution"], {"2": 217, "3": 3}
        )
        self.assertEqual(progress["admitted_search_query_distribution"], {"4": 220})
        self.assertTrue(
            self.summary["mechanical_conclusion"][
                "all_fallbacks_completed_plan_retrieval_page_projection_and_synthesis_progress"
            ]
        )

    def test_report_is_sealed_and_does_not_authorize_benchmark(self) -> None:
        value = target.build_report(now=1, require_clean=False)
        target.validate_report(value)
        self.assertFalse(value["authorization"]["benchmark_or_exact220_launch"])
        self.assertFalse(value["authorization"]["evaluator_or_revaluation"])

    def test_source_has_fixed_receipt_allowlist_and_no_evaluator_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
        self.assertEqual(
            set(target.RECEIPT_NAMES),
            {
                "child_terminal_receipt.json",
                "base_parent_exit_receipt.json",
                "keyless_coverage_parent_bundle_receipt.json",
                "mapping_recovery_stage_receipt.json",
                "safe_progress.json",
            },
        )
        self.assertNotIn("visible_task.json\")", source)
        self.assertNotIn("runtime_predictions", source)
        self.assertNotIn("official_eval", source)


if __name__ == "__main__":
    unittest.main()
