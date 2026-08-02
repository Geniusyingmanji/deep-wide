from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RunV24268KeylessBatchedTaskTests(unittest.TestCase):
    def source(self) -> str:
        return (ROOT / "scripts/run_v24268_keyless_batched_task.py").read_text(
            encoding="utf-8"
        )

    def test_entrypoint_has_no_credential_dependency_or_privileged_data_source(self) -> None:
        source = self.source()
        ast.parse(source)
        self.assertNotIn("ANTHROPIC_API_KEY", source)
        self.assertNotIn("TAVILY_API", source)
        for forbidden in (
            "question_type",
            "ground_truth",
            "answer_key",
            "evaluator_mapping",
            "results.csv",
        ):
            self.assertNotIn(forbidden, source)

    def test_entrypoint_freezes_same_width_and_single_proxy_search_worker(self) -> None:
        source = self.source()
        self.assertIn('default="http://127.0.0.1:9878/responses"', source)
        self.assertIn('"--search-batch-size", type=int, default=8', source)
        self.assertIn('"--search-workers", type=int, default=1', source)
        self.assertIn('"--search-queries", type=int, default=8', source)
        self.assertIn('"--fetch-targets", type=int, default=16', source)
        self.assertIn("fetch_pages=False", source)


if __name__ == "__main__":
    unittest.main()
