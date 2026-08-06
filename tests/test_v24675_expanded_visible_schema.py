from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from deepwide_agent.v24675_expanded_visible_schema import (  # noqa: E402
    extract_expanded_visible_columns,
)


class V24675ExpandedVisibleSchemaTests(unittest.TestCase):
    def test_frozen_parser_result_is_preserved(self) -> None:
        question = "表格中的列名依次为：时间、赛事、名次。不要提问。"
        self.assertEqual(
            extract_expanded_visible_columns(question),
            extract_robust_visible_columns(question),
        )

    def test_chinese_must_contain_and_colonless_declarations(self) -> None:
        self.assertEqual(
            extract_expanded_visible_columns(
                "请输出表格，表格必须包含以下列：赛事名称、时间、名次。"
            ),
            ["赛事名称", "时间", "名次"],
        )
        self.assertEqual(
            extract_expanded_visible_columns(
                "输出采用中文，列名依次为招聘单位、招聘岗位、招聘人数、报名时间。"
            ),
            ["招聘单位", "招聘岗位", "招聘人数", "报名时间"],
        )

    def test_english_with_columns_pipe_and_comma_forms(self) -> None:
        self.assertEqual(
            extract_expanded_visible_columns(
                "Please output one Markdown table with the columns, in this exact order:\n"
                "Project | Sea / Basin | Capacity (MW) | Owner / Operator\n"
                "Fill missing fields with NA."
            ),
            ["Project", "Sea / Basin", "Capacity (MW)", "Owner / Operator"],
        )
        self.assertEqual(
            extract_expanded_visible_columns(
                "Present the data in one Markdown table with columns: Device, "
                "Available colors, Announced date, RAM. Do not omit cells."
            ),
            ["Device", "Available colors", "Announced date", "RAM"],
        )

    def test_dotted_abbreviation_does_not_end_column_clause(self) -> None:
        self.assertEqual(
            extract_expanded_visible_columns(
                "Present the data in one Markdown table with columns: Device, "
                "RAM, U.S. launch price (MSRP by storage), Materials, Battery capacity."
            ),
            [
                "Device",
                "RAM",
                "U.S. launch price (MSRP by storage)",
                "Materials",
                "Battery capacity",
            ],
        )

    def test_long_comma_separated_prose_remains_ambiguous(self) -> None:
        long_name = "University ranking system " + "with global reputation evidence " * 6
        question = (
            "Please organize the results in one Markdown table with the following columns: "
            f"Subject, {long_name}, Home Page, Application Fee."
        )
        self.assertEqual(extract_expanded_visible_columns(question), [])

    def test_information_includes_and_columns_labeled(self) -> None:
        self.assertEqual(
            extract_expanded_visible_columns(
                "需要整理的信息包括案件日期、所在州、发生场所、死亡人数。"
                "请以一个表格输出。"
            ),
            ["案件日期", "所在州", "发生场所", "死亡人数"],
        )
        self.assertEqual(
            extract_expanded_visible_columns(
                "Please organize one table with columns labeled: Date, Event Name, "
                "Level, Result."
            ),
            ["Date", "Event Name", "Level", "Result"],
        )

    def test_ambiguous_or_absent_declaration_still_fails_closed(self) -> None:
        self.assertEqual(
            extract_expanded_visible_columns(
                "Please include the following details for each model without listing fields."
            ),
            [],
        )
        self.assertEqual(
            extract_expanded_visible_columns(
                "The columns should describe monthly employment statistics but are not named."
            ),
            [],
        )

    def test_source_has_no_privileged_runtime_access(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24675_expanded_visible_schema.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
