from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as contract
from deepwide_agent.v24804_shared_prefix_budget_ladder import ARMS
from scripts import evaluate_v24809_worldbank_budget_ladder_smoke as target


COUNTRIES = (("Alpha", "AAA"), ("Beta", "BBB"), ("Gamma", "CCC"), ("Delta", "DDD"))


def question() -> str:
    countries = "\n".join(
        f"{index}. {name} [{iso3}]"
        for index, (name, iso3) in enumerate(COUNTRIES, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f"{item['label']} [{item['indicator']}] @{item['year']}"
                for item in contract.TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by "
        "the official API. Use Unknown when unavailable. Return one table only."
    )


def gold() -> list[dict[str, str]]:
    columns = [
        f"{item['label']} [{item['indicator']}] @{item['year']}"
        for item in contract.TARGETS
    ]
    return [
        {"Country": name, columns[0]: f"{index}.10", columns[1]: f"{index}.20"}
        for index, (name, _iso3) in enumerate(COUNTRIES, 1)
    ]


def table(*, complete: bool) -> str:
    columns = [
        "Country",
        *(
            f"{item['label']} [{item['indicator']}] @{item['year']}"
            for item in contract.TARGETS
        ),
    ]
    rows = []
    for index, (name, _iso3) in enumerate(COUNTRIES, 1):
        values = [f"{index}.10", f"{index}.20"] if complete else [f"{index}.10", "Unknown"]
        rows.append(f"| {name} | {values[0]} | {values[1]} |")
    return (
        "```markdown\n| " + " | ".join(columns) + " |\n"
        "| --- | --- | --- |\n" + "\n".join(rows) + "\n```"
    )


class V24809EvaluatorTests(unittest.TestCase):
    def test_exact_and_partial_metrics(self):
        exact = target.evaluate_prediction(table(complete=True), question(), gold())
        partial = target.evaluate_prediction(table(complete=False), question(), gold())
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)
        self.assertEqual(partial["exact_table_success"], 0)
        self.assertLess(partial["item_f1"], exact["item_f1"])

    def test_fixed_denominator_three_arm_gate(self):
        visible_tasks = []
        predictions = []
        expected = {}
        for index in range(1, contract.SELECTED_COUNT + 1):
            opaque = f"task_{0x248090 + index:024x}"
            visible_tasks.append({"opaque_id": opaque, "question": question()})
            expected[opaque] = gold()
            predictions.append(
                {
                    "opaque_id": opaque,
                    "predictions": {
                        "first_wave_only": table(complete=False),
                        "fixed_full_budget": table(complete=True),
                        "coverage_risk_adaptive": table(complete=True),
                    },
                }
            )
        metrics = target.evaluate_rows(
            predictions, {"visible_tasks": visible_tasks}, expected
        )
        self.assertEqual(set(metrics["arms"]), set(ARMS))
        self.assertEqual(
            metrics["arms"]["fixed_full_budget"]["exact_table_successes"],
            contract.SELECTED_COUNT,
        )
        self.assertGreater(
            metrics["fixed_full_minus_first_wave"]["exact_table_successes"], 0
        )
        self.assertTrue(metrics["mechanism_gate_passed"])

    def test_evaluator_is_excluded_from_forward_manifest(self):
        evaluator = Path("scripts/evaluate_v24809_worldbank_budget_ladder_smoke.py")
        self.assertNotIn(evaluator, contract.RUNTIME_SOURCES)
        self.assertTrue(
            all(relative.parts[:1] != ("evaluation",) for relative in contract.RUNTIME_SOURCES)
        )


if __name__ == "__main__":
    unittest.main()
