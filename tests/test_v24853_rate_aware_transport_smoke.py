from __future__ import annotations

import ast
import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24853_rate_aware_transport_smoke as smoke  # noqa: E402


class V24853RateAwareTransportSmokeTests(unittest.TestCase):
    def test_query_vector_is_small_neutral_and_fixed(self) -> None:
        queries = smoke.neutral_queries()
        self.assertEqual(len(queries), 4)
        self.assertTrue(all(isinstance(query, str) and query.strip() for query in queries))

    def test_protocol_is_aggregate_only_and_exact220_is_not_authorized(self) -> None:
        source = (ROOT / "scripts/v24853_rate_aware_transport_smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"exact220_launch": False', source)
        self.assertTrue(
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read"
            in source
        )

    def test_credentials_require_twelve_distinct_lines(self) -> None:
        values = [f"neutral-secret-{index:02d}" for index in range(12)]
        self.assertEqual(
            smoke.ephemeral_credentials(io.StringIO("\n".join(values))),
            tuple(values),
        )
        with self.assertRaises(RuntimeError):
            smoke.ephemeral_credentials(io.StringIO("one\n"))

    def test_runtime_has_no_evaluator_import(self) -> None:
        source = (ROOT / "scripts/v24853_rate_aware_transport_smoke.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
