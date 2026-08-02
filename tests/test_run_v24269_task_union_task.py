from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RunV24269TaskUnionTaskTests(unittest.TestCase):
    def test_entrypoint_is_keyless_label_blind_and_same_width(self) -> None:
        source = (ROOT / "scripts/run_v24269_task_union_task.py").read_text(
            encoding="utf-8"
        )
        ast.parse(source)
        for forbidden in (
            "ANTHROPIC_API_KEY",
            "TAVILY_API",
            "question_type",
            "ground_truth",
            "answer_key",
            "evaluator_mapping",
            "results.csv",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"--search-batch-size", type=int, default=8', source)
        self.assertIn('"--search-workers", type=int, default=1', source)
        self.assertIn('"--search-queries", type=int, default=8', source)
        self.assertIn('"--fetch-targets", type=int, default=16', source)
        self.assertIn("fetch_pages=False", source)


if __name__ == "__main__":
    unittest.main()
