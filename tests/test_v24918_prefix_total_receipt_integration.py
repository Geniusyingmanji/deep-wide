from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24918_prefix_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24916_prefix_total_long_page_packer import (  # noqa: E402
    build_prefix_total_packing,
)
from scripts import run_v24918_prefix_total_exact220 as runner  # noqa: E402


QUESTION = "Return one table with columns: Country | Target Metric. Omega Republic [OMG]"


class V24918PrefixTotalReceiptIntegrationTests(unittest.TestCase):
    def test_aggregate_requires_exactly_220_receipts(self) -> None:
        original_root = contract.TASK_ROOT
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            contract.TASK_ROOT = Path(directory).relative_to(ROOT)
            try:
                with self.assertRaises(RuntimeError):
                    runner.validate_projection_receipts()
            finally:
                contract.TASK_ROOT = original_root

    def test_aggregate_counts_totality_fallback_and_query_aware_path(self) -> None:
        original_root = contract.TASK_ROOT
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            task_root = Path(directory)
            contract.TASK_ROOT = task_root.relative_to(ROOT)
            try:
                for position in range(1, 221):
                    path = task_root / f"task_{position:04d}"
                    path.mkdir()
                    if position == 1:
                        content = (("Entity Value " + "x" * 40) + "\n\n") * 200
                    elif position == 2:
                        content = "boilerplate " * 600 + "\nOmega Republic [OMG]: 999"
                    else:
                        content = "Omega Republic [OMG]: 999"
                    receipt = build_prefix_total_packing(
                        QUESTION,
                        [{"title": "Official", "url": "https://example.invalid", "content": content}],
                    )["content_free_receipt"]
                    runner.base.algorithm._new_json(path / "projection_receipt.json", receipt)
                counts = runner.validate_projection_receipts()
            finally:
                contract.TASK_ROOT = original_root
        self.assertEqual(counts["projection_receipts_present_and_valid"], 220)
        self.assertEqual(counts["tasks_with_structural_totality_fallback"], 1)
        self.assertEqual(counts["tasks_with_engaged_mechanism"], 1)

    def test_empty_terminal_receipt_is_valid(self) -> None:
        receipt = build_prefix_total_packing("visible terminal fallback", [])[
            "content_free_receipt"
        ]
        self.assertEqual(receipt["input_page_count"], 0)
        self.assertFalse(receipt["structural_cap_totality_fallback_applied"])
        self.assertFalse(receipt["long_page_mechanism_engaged"])

    def test_receipt_contains_no_benchmark_or_evidence_content(self) -> None:
        receipt = build_prefix_total_packing(
            QUESTION,
            [{"content": "boilerplate " * 600 + "Omega Republic [OMG]: 999"}],
        )["content_free_receipt"]
        self.assertFalse(
            receipt[
                "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential"
            ]
        )
        self.assertFalse(
            receipt[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_entropy_never_assigns_signed_credit(self) -> None:
        receipt = build_prefix_total_packing(QUESTION, [])["content_free_receipt"]
        self.assertTrue(receipt["entropy_information_gain_shadow_only"])
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])


if __name__ == "__main__":
    unittest.main()
