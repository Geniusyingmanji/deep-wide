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
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
    run_v24286_task,
    validate_v24286_result,
)
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402


class FakeModel:
    def __init__(self, values):
        self.values = list(values)
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


def limits():
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class V24286VisibleSchemaRuntimeTests(unittest.TestCase):
    def test_parser_preserves_nested_commas_leading_digits_and_sentence_boundary(self):
        self.assertEqual(
            extract_robust_visible_columns(
                "表格中的列名依次为：时间、1/16赛-对手、1/16赛比分。不要问我问题。"
            ),
            ["时间", "1/16赛-对手", "1/16赛比分"],
        )
        self.assertEqual(
            extract_robust_visible_columns(
                "Use a table. The column names are: Model Name, Price (USD, launch MSRPs), "
                "Dimensions L/W/H (mm), and Address. Format the date separately."
            ),
            ["Model Name", "Price (USD, launch MSRPs)", "Dimensions L/W/H (mm)", "Address"],
        )

    def test_parser_handles_pipe_list_on_following_line_and_quoted_date_example(self):
        question = (
            "Provide one Markdown table with the following columns (in the exact order):\n"
            "Project | State | Start Year | Completion Year | Final Total Cost\n"
            "Notes: use NA when unavailable."
        )
        self.assertEqual(
            extract_robust_visible_columns(question),
            ["Project", "State", "Start Year", "Completion Year", "Final Total Cost"],
        )
        quoted = (
            "The column names in the table are: Product, Release Date, and Memory. "
            'The release date should be formatted as "September 12, 2012."'
        )
        self.assertEqual(
            extract_robust_visible_columns(quoted),
            ["Product", "Release Date", "Memory"],
        )
        self.assertEqual(
            extract_robust_visible_columns(
                "表格中的列名依次为：年份 企业 收益（百万） 入住率。不要提问。"
            ),
            ["年份", "企业", "收益（百万）", "入住率"],
        )
        self.assertEqual(
            extract_robust_visible_columns(
                "The column names are: Name, Mission Status. Launch date should be yyyy-mm-dd."
            ),
            ["Name", "Mission Status"],
        )
        self.assertEqual(
            extract_robust_visible_columns(
                "The column names are: Date, the Concert's English Name, Host City."
            ),
            ["Date", "the Concert's English Name", "Host City"],
        )
        self.assertEqual(
            extract_robust_visible_columns(
                "表格中的列名依次为：名称、日期、地址，如果无法获取则填NA。"
            ),
            ["名称", "日期", "地址"],
        )

    def test_end_to_end_forces_visible_schema_and_attributes_nested_timing(self):
        task = {
            "opaque_id": "task_" + "0" * 24,
            "question": (
                "Return a Markdown table. The column names are: Model Name, "
                "Price (USD, launch MSRPs), and Release Date. "
                "The release date should be yyyy-mm-dd."
            ),
        }
        plan = json.dumps(
            {
                "language": "English",
                "columns": ["wrong", "columns"],
                "queries": ["visible one", "visible two", "visible three", "visible four"],
            }
        )
        table = """```markdown
| Model Name | Price (USD, launch MSRPs) | Release Date |
| --- | --- | --- |
| Example | 10 | 2026-01-01 |
```"""
        result = run_v24286_task(
            task,
            model=FakeModel([plan, table]),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24286_result(result)
        self.assertEqual(
            result["columns"],
            ["Model Name", "Price (USD, launch MSRPs)", "Release Date"],
        )
        self.assertEqual(result["visible_schema"]["status"], "applied")
        timing = result["attributed_timing"]
        self.assertEqual(timing["status"], "complete")
        self.assertGreater(timing["provider_search_seconds"], 0)
        self.assertGreater(timing["network_fetch_seconds"], 0)
        self.assertAlmostEqual(
            timing["provider_search_seconds"]
            + timing["network_fetch_seconds"]
            + timing["controller_and_adapter_seconds"],
            timing["retrieval_envelope_seconds"],
            places=6,
        )
        encoded = json.dumps(
            {"schema": result["visible_schema"], "timing": timing},
            ensure_ascii=False,
        )
        for forbidden in ("Model Name", "visible one", "Example", task["opaque_id"]):
            self.assertNotIn(forbidden, encoded)

    def test_ascii_quotes_and_escaped_pipes_are_entity_encoded(self):
        task = {
            "opaque_id": "task_" + "1" * 24,
            "question": "The column names are: Product, Description, and Date. Please return a table.",
        }
        plan = json.dumps({"columns": ["bad"], "queries": ["one", "two"]})
        table = """| Product | Description | Date |
| --- | --- | --- |
| Card | 2\\|3 inch \"edition | 2026-01-01 |
"""
        result = run_v24286_task(
            task,
            model=FakeModel([plan, table]),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24286_result(result)
        self.assertIn("2&#124;3 inch &quot;edition", result["prediction"])
        event = result["visible_schema"]["events"][1]
        self.assertEqual(event["escaped_pipe_entities"], 1)
        self.assertEqual(event["quote_entities"], 1)

    def test_plan_provider_failure_preserves_visible_schema(self):
        task = {
            "opaque_id": "task_" + "3" * 24,
            "question": "The column names are: Name, Version, and Date. Return a table.",
        }
        table = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
        result = run_v24286_task(
            task,
            model=FakeModel([RuntimeError("private planner failure"), table]),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24286_result(result)
        self.assertEqual(result["columns"], ["Name", "Version", "Date"])
        self.assertEqual(
            result["visible_schema"]["events"][0]["status"],
            "forced_visible_schema_after_provider_failure",
        )
        self.assertNotIn("private planner failure", json.dumps(result))

    def test_receipt_tamper_and_privileged_input_fail_closed(self):
        task = {
            "opaque_id": "task_" + "2" * 24,
            "question": "The column names are: Name, Version, and Date. Return a table.",
        }
        plan = json.dumps({"columns": ["bad"], "queries": ["one", "two"]})
        table = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"
        result = run_v24286_task(
            task,
            model=FakeModel([plan, table]),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        tampered = copy.deepcopy(result)
        tampered["attributed_timing"]["provider_search_seconds"] += 1
        with self.assertRaises(ValueError):
            validate_v24286_result(tampered)
        model = FakeModel([plan, table])
        search = FakeSearch()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24286_task(
                {**task, "category": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
