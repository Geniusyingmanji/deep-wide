from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25541_visible_output_constraint_contract as contracts  # noqa: E402
from deepwide_agent import v25544_deterministic_visible_constraint_projector as target  # noqa: E402
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


class V25544DeterministicVisibleConstraintProjectorTests(unittest.TestCase):
    def test_complete_dates_reformat_without_precision_invention(self) -> None:
        columns = ["Event", "Date"]
        contract = contracts.build_contract(
            "Format Date as YYYY/MM/DD.", columns
        )
        base = table(
            columns,
            [["A", "Jan 02, 2020"], ["B", "2021"], ["C", "2020-13-02"]],
        )
        value = target.build_projection(base, contract)
        receipt = value["content_free_receipt"]
        self.assertIn("2020/01/02", value["candidate_prediction"])
        self.assertIn("| B | 2021 |", value["candidate_prediction"])
        self.assertIn("| C | 2020-13-02 |", value["candidate_prediction"])
        self.assertEqual(receipt["date_cell_examined_count"], 3)
        self.assertEqual(receipt["date_cell_changed_count"], 1)
        self.assertEqual(receipt["date_cell_rejected_count"], 2)

    def test_scale_conversion_preserves_surrounding_text_and_rejects_ambiguity(self) -> None:
        columns = ["Country", "GDP"]
        contract = contracts.build_contract("Report GDP in trillions.", columns)
        base = table(
            columns,
            [
                ["A", "$4,896 billion"],
                ["B", "1.8 trillion"],
                ["C", "between 4 and 5 billion"],
                ["D", "45%"],
            ],
        )
        value = target.build_projection(base, contract)
        prediction = value["candidate_prediction"]
        receipt = value["content_free_receipt"]
        self.assertIn("$4.896 trillion", prediction)
        self.assertIn("| B | 1.8 trillion |", prediction)
        self.assertIn("between 4 and 5 billion", prediction)
        self.assertIn("| D | 45% |", prediction)
        self.assertEqual(receipt["scale_cell_changed_count"], 1)
        self.assertEqual(receipt["scale_cell_rejected_count"], 2)

    def test_stable_sort_requires_complete_single_kind_values(self) -> None:
        columns = ["Name", "Score"]
        contract = contracts.build_contract(
            "Sort by Score in descending order.", columns
        )
        base = table(columns, [["A", "7"], ["B", "9"], ["C", "9"]])
        value = target.build_projection(base, contract)
        self.assertEqual(
            value["candidate_prediction"].splitlines()[3:],
            ["| B | 9 |", "| C | 9 |", "| A | 7 |", "```"],
        )
        self.assertEqual(value["content_free_receipt"]["sort_applied_count"], 1)
        unknown = table(columns, [["A", "7"], ["B", "Unknown"]])
        rejected = target.build_projection(unknown, contract)
        self.assertEqual(rejected["candidate_prediction"], unknown)
        self.assertEqual(
            rejected["content_free_receipt"]["sort_rejected_count"], 1
        )

    def test_temporal_range_and_rank_slot_never_mutate_rows(self) -> None:
        columns = ["Year", "Rank", "Team"]
        contract = contracts.build_contract(
            "For 2019-2020 return Top 2 teams with Rank and Team.", columns
        )
        base = table(
            columns,
            [["2018", "3", "X"], ["2019", "1", "A"], ["2020", "2", "B"]],
        )
        value = target.build_projection(base, contract)
        self.assertEqual(value["candidate_prediction"], base)
        self.assertFalse(value["candidate_prediction_changed"])

    def test_noncanonical_shape_and_resealed_tamper_fail_closed(self) -> None:
        contract = contracts.build_contract(
            "Format Date as YYYY-MM-DD.", ["Event", "Date"]
        )
        with self.assertRaises(ValueError):
            target.build_projection("not a table", contract)
        value = target.build_projection(
            table(["Event", "Date"], [["A", "Jan 02, 2020"]]), contract
        )
        changed = copy.deepcopy(value)
        changed["candidate_prediction"] = changed["control_prediction"]
        changed["candidate_prediction_changed"] = False
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_projection(changed, contract=contract)

    def test_zero_external_capability_and_zero_credit(self) -> None:
        integration = target.integration_contract()
        self.assertFalse(integration["temporal_range_row_filtering"])
        self.assertFalse(integration["rank_slot_row_insertion_deletion_or_relabeling"])
        self.assertFalse(integration["partial_date_precision_invention"])
        self.assertFalse(
            integration[
                "additional_model_search_fetch_token_context_wall_or_network_budget"
            ]
        )
        self.assertEqual(integration["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
