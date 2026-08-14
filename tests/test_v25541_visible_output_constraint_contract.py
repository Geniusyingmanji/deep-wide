from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25541_visible_output_constraint_contract as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


def table(columns: list[str], rows: list[list[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


class V25541VisibleOutputConstraintContractTests(unittest.TestCase):
    def test_no_constraint_is_empty_suffix_and_zero_credit(self) -> None:
        contract = target.build_contract(
            "List the package and its maintainer.", ["Package", "Maintainer"]
        )
        self.assertEqual(contract["active_families"], [])
        self.assertEqual(contract["active_family_count"], 0)
        self.assertEqual(target.contract_suffix(contract), "")
        self.assertEqual(contract["positive_signed_credit_count"], 0)

    def test_temporal_range_and_date_format_are_exact_and_ambiguous_fails(self) -> None:
        columns = ["Year", "Event Date", "Value"]
        contract = target.build_contract(
            "Return annual rows from 2018 through 2020. Format Event Date as YYYY-MM-DD.",
            columns,
        )
        self.assertEqual(
            contract["temporal_year_range"],
            {
                "inclusive_start_year": 2018,
                "inclusive_end_year": 2020,
                "target_columns": ["Year", "Event Date"],
                "row_scope_applies_even_without_year_column": False,
            },
        )
        self.assertEqual(contract["date_format"]["style"], "iso_dash")
        self.assertIn("VISIBLE OUTPUT CONSTRAINT CONTRACT:", target.contract_suffix(contract))
        conflicting = target.build_contract(
            "Use 2018-2020 and 2021-2022. Format Date as YYYY-MM-DD or YYYY/MM/DD.",
            ["Date", "Value"],
        )
        self.assertIsNone(conflicting["temporal_year_range"])
        self.assertIsNone(conflicting["date_format"])

    def test_numeric_scale_requires_one_explicit_scale(self) -> None:
        contract = target.build_contract(
            "Report GDP expressed in billions.", ["Country", "GDP"]
        )
        self.assertEqual(contract["numeric_scale"]["scale"], "billion")
        self.assertEqual(contract["numeric_scale"]["target_columns"], ["GDP"])
        ambiguous = target.build_contract(
            "The source has millions but output may use billions.", ["Country", "GDP"]
        )
        self.assertIsNone(ambiguous["numeric_scale"])
        incidental = target.build_contract(
            "Describe the Million Dollar Quartet.", ["Work", "Artist"]
        )
        self.assertIsNone(incidental["numeric_scale"])

    def test_rank_slots_and_explicit_order_are_conservative(self) -> None:
        rank = target.build_contract(
            "Return the Top 3 teams with Rank and Team columns.",
            ["Rank", "Team"],
        )
        self.assertEqual(rank["rank_slots"]["required_rank_values"], ["1", "2", "3"])
        tied = target.build_contract(
            "Return the Top 3 teams including ties.", ["Rank", "Team"]
        )
        self.assertIsNone(tied["rank_slots"])
        ordered = target.build_contract(
            "Sort by Revenue in descending order.", ["Company", "Revenue"]
        )
        self.assertEqual(
            ordered["explicit_order"],
            {
                "target_column": "Revenue",
                "direction": "descending",
                "value_kind": "numeric_or_lexical",
            },
        )
        vague = target.build_contract(
            "Return the ranking in the requested order.", ["Rank", "Team"]
        )
        self.assertIsNone(vague["explicit_order"])

    def test_content_free_observer_checks_format_range_scale_rank_and_order(self) -> None:
        temporal = target.build_contract(
            "Use 2019-2020 and format Date as YYYY-MM-DD.",
            ["Date", "Value"],
        )
        good = target.observe_prediction(
            temporal,
            table(
                ["Date", "Value"],
                [["2019-01-02", "A"], ["2020-03-04", "B"]],
            ),
        )
        self.assertTrue(good["temporal_year_range_satisfied"])
        self.assertTrue(good["date_format_satisfied"])
        bad = target.observe_prediction(
            temporal,
            table([["Date", "Value"]][0], [["2021/01/02", "A"]]),
        )
        self.assertEqual(bad["temporal_out_of_range_cell_count"], 1)
        self.assertEqual(bad["date_format_violation_cell_count"], 1)

        rank = target.build_contract(
            "Return Top 3 rows sorted by Score in descending order.",
            ["Rank", "Name", "Score"],
        )
        observed = target.observe_prediction(
            rank,
            table(
                ["Rank", "Name", "Score"],
                [["1", "A", "9"], ["2", "B", "8"], ["3", "C", "7"]],
            ),
        )
        self.assertTrue(observed["rank_slots_satisfied"])
        self.assertTrue(observed["explicit_order_satisfied"])

        scale = target.build_contract(
            "Report Revenue in millions.", ["Company", "Revenue"]
        )
        conflict = target.observe_prediction(
            scale, table(["Company", "Revenue"], [["A", "2 billion"]])
        )
        self.assertEqual(conflict["conflicting_scale_cell_count"], 1)

    def test_resealed_contract_and_observation_tamper_fail(self) -> None:
        contract = target.build_contract(
            "Return Top 2 teams.", ["Rank", "Team"]
        )
        changed = copy.deepcopy(contract)
        changed["rank_slots"]["count"] = 3
        changed.pop("contract_payload_sha256")
        changed["contract_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_contract(changed)

        observation = target.observe_prediction(
            contract, table(["Rank", "Team"], [["1", "A"], ["2", "B"]])
        )
        changed_observation = copy.deepcopy(observation)
        changed_observation["positive_signed_credit_count"] = 1
        changed_observation.pop("observation_payload_sha256")
        changed_observation["observation_payload_sha256"] = payload_sha256(
            changed_observation
        )
        with self.assertRaises(ValueError):
            target.validate_observation(changed_observation)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25541_visible_output_constraint_contract.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertNotIn("from . import runtime", source)
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
