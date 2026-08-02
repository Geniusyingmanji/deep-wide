from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    DeterministicNormalizingModel,
    normalize_candidate_table,
    run_v24259_task,
    validate_v24259_result,
)


COLUMNS = ["名称", "省份", "年份"]
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、省份、年份。只输出Markdown表格。",
}


class FakeModel:
    def __init__(self, outputs: list[str | BaseException]) -> None:
        self.outputs = list(outputs)
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.outputs.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class FakeSearch:
    calls = 0
    failures = 0
    tool_calls = 0
    fetch_calls = 0
    fetch_failures = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    def search_many(self, queries, **kwargs):
        self.calls += len(queries)
        return []

    def fetch_urls(self, requests_):
        self.fetch_calls += len(requests_)
        return []


PLAN = json.dumps(
    {"language": "中文", "columns": COLUMNS, "queries": ["visible query"]},
    ensure_ascii=False,
)


class DeterministicTableNormalizerTests(unittest.TestCase):
    def test_reorders_visible_headers_without_changing_cells(self) -> None:
        raw = """年份 | 名称 | 省份
--- | --- | ---
2024 | 甲 | 北京
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertEqual(audit["mode"], "reordered")
        self.assertIn("| 甲 | 北京 | 2024 |", table)

    def test_positional_header_replacement_and_empty_marker_are_structural(self) -> None:
        raw = """| Name | Location | Year |
| :--- | ---: | --- |
| 甲 |  | 2024 |
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertEqual(audit["mode"], "positional_header")
        self.assertEqual(audit["filled_empty_cell_count"], 1)
        self.assertIn("| 甲 | 未知 | 2024 |", table)

    def test_drops_only_an_explicit_generic_index_column(self) -> None:
        raw = """| 序号 | 名称 | 省份 | 年份 |
| --- | --- | --- | --- |
| 1 | 甲 | 北京 | 2024 |
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertEqual(audit["mode"], "drop_index")
        self.assertNotIn("| 1 |", table)
        self.assertIn("| 甲 | 北京 | 2024 |", table)

    def test_ambiguous_extra_column_is_rejected(self) -> None:
        raw = """| 名称 | 城市 | 省份 | 年份 |
| --- | --- | --- | --- |
| 甲 | 北京市 | 北京 | 2024 |
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertIsNone(table)
        self.assertEqual(audit["status"], "unrecoverable")

    def test_malformed_data_row_rejects_partial_table_deletion(self) -> None:
        raw = """| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 甲 | 北京 | 2024 |
| 乙 | 上海 |
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertIsNone(table)
        self.assertEqual(audit["status"], "unrecoverable")

    def test_escaped_pipe_is_deferred_to_parent_repair(self) -> None:
        raw = """| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 甲\\|乙 | 北京 | 2024 |
"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertIsNone(table)
        self.assertEqual(audit["status"], "unrecoverable")

    def test_exact_canonical_candidate_is_not_claimed_as_normalized(self) -> None:
        raw = """```markdown
| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 甲 | 北京 | 2024 |
```"""
        table, audit = normalize_candidate_table(raw, COLUMNS, unknown_marker="未知")
        self.assertEqual(table, raw)
        self.assertEqual(audit["status"], "exact")

    def test_proxy_normalizes_synthesis_before_model_repair(self) -> None:
        malformed = """Name | Province | Year
--- | --- | ---
甲 | 北京 | 2024
"""
        model = FakeModel([PLAN, malformed])
        result = run_v24259_task(
            TASK,
            model=model,
            search=FakeSearch(),
            limits=ScoreFirstLimits(search_queries=1, fetch_targets=1),
            monotonic=lambda: 1.0,
        )
        validate_v24259_result(result)
        self.assertEqual(result["completion_kind"], "normalized_primary")
        self.assertEqual(model.requests, 2)
        self.assertEqual(result["normalization"]["events"][0]["mode"], "positional_header")

    def test_unrecoverable_candidate_still_uses_one_bounded_repair(self) -> None:
        bad = "no table"
        repaired = """| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 甲 | 北京 | 2024 |
"""
        model = FakeModel([PLAN, bad, repaired])
        result = run_v24259_task(
            TASK,
            model=model,
            search=FakeSearch(),
            limits=ScoreFirstLimits(search_queries=1, fetch_targets=1),
            monotonic=lambda: 1.0,
        )
        validate_v24259_result(result)
        self.assertEqual(result["completion_kind"], "normalized_repaired")
        self.assertEqual(model.requests, 3)

    def test_without_explicit_visible_columns_normalizer_does_not_rewrite(self) -> None:
        question = "请研究并以表格返回结果。"
        model = FakeModel([PLAN, "Name | Province | Year\n--- | --- | ---\n甲 | 北京 | 2024"])
        proxy = DeterministicNormalizingModel(
            model,
            question=question,
            limits=ScoreFirstLimits(),
        )
        proxy.complete("plan", "plan", max_output_tokens=100, json_mode=True)
        result = proxy.complete("synthesis", "synthesis", max_output_tokens=100)
        self.assertNotIn("```markdown", result.text)
        self.assertEqual(proxy.events[0]["mode"], "no_explicit_visible_columns")

    def test_privileged_task_field_is_rejected_before_effect(self) -> None:
        model = FakeModel([PLAN])
        task = copy.deepcopy(TASK)
        task["category"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24259_task(task, model=model, search=FakeSearch())
        self.assertEqual(model.requests, 0)


if __name__ == "__main__":
    unittest.main()
