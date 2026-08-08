from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24914_cap_bound_long_page_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24913_observable_long_page_packer import (  # noqa: E402
    build_observable_packing,
)
from scripts import run_v24914_cap_bound_long_page_exact220 as runner  # noqa: E402
from scripts import run_v24914_cap_bound_long_page_exact220_task as child  # noqa: E402


QUESTION = (
    "Return one table with columns: Country | Target Metric.\n"
    "<COUNTRIES>Omega Republic [OMG]</COUNTRIES>"
)


class V24914ProjectionReceiptIntegrationTests(unittest.TestCase):
    def test_aggregate_requires_exactly_220_receipts(self) -> None:
        original_root = contract.TASK_ROOT
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            contract.TASK_ROOT = Path(directory).relative_to(ROOT)
            try:
                with self.assertRaises(RuntimeError):
                    runner.validate_projection_receipts()
            finally:
                contract.TASK_ROOT = original_root

    def test_aggregate_validates_and_sums_content_free_receipts(self) -> None:
        original_root = contract.TASK_ROOT
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            task_root = Path(directory)
            contract.TASK_ROOT = task_root.relative_to(ROOT)
            try:
                for position in range(1, 221):
                    path = task_root / f"task_{position:04d}"
                    path.mkdir()
                    content = (
                        "boilerplate " * 600 + "\nOmega Republic [OMG]: 999"
                        if position == 1
                        else "Omega Republic [OMG]: 999"
                    )
                    receipt = build_observable_packing(
                        QUESTION,
                        [
                            {
                                "title": "Official",
                                "url": "https://official.example/data",
                                "content": content,
                            }
                        ],
                    )["content_free_receipt"]
                    runner.base.algorithm._new_json(
                        path / "projection_receipt.json", receipt
                    )
                counts = runner.validate_projection_receipts()
            finally:
                contract.TASK_ROOT = original_root
        self.assertEqual(counts["projection_receipts_present_and_valid"], 220)
        self.assertEqual(counts["tasks_with_long_pages"], 1)
        self.assertEqual(counts["tasks_with_engaged_mechanism"], 1)
        self.assertGreater(counts["input_characters_beyond_output_page_cap"], 0)

    def test_receipt_contains_no_benchmark_or_evidence_content(self) -> None:
        receipt = build_observable_packing(
            QUESTION,
            [
                {
                    "title": "Official",
                    "url": "https://official.example/data",
                    "content": "boilerplate " * 600
                    + "\nOmega Republic [OMG]: 999",
                }
            ],
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

    def test_receipt_entropy_never_assigns_signed_credit(self) -> None:
        receipt = build_observable_packing(
            QUESTION,
            [{"content": "Omega Republic [OMG]: 999"}],
        )["content_free_receipt"]
        self.assertTrue(receipt["entropy_information_gain_shadow_only"])
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])

    def test_terminal_fallback_receipt_is_zero_page_and_unengaged(self) -> None:
        receipt = build_observable_packing("visible terminal fallback", [
        ])["content_free_receipt"]
        self.assertEqual(receipt["input_page_count"], 0)
        self.assertEqual(receipt["long_page_packed_count"], 0)
        self.assertFalse(receipt["long_page_mechanism_engaged"])
        self.assertFalse(
            receipt[
                "contains_question_query_url_host_page_content_projection_hash_opaque_id_or_credential"
            ]
        )


if __name__ == "__main__":
    unittest.main()
